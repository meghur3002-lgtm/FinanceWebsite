from flask import Flask, render_template, request, redirect, url_for, flash
from database import get_connection, initialize_database
from datetime import datetime
from zoneinfo import ZoneInfo
import os


app = Flask(__name__)
app.secret_key = "finance-management-secret-key"

INDIA_TIMEZONE = ZoneInfo("Asia/Kolkata")


# ============================================================
# DATE FILTER
# ============================================================

@app.template_filter("display_date")
def display_date(value):

    if not value:
        return ""

    try:

        return datetime.strptime(
            str(value),
            "%Y-%m-%d"
        ).strftime("%d-%m-%Y")

    except (ValueError, TypeError):

        return value


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    conn = get_connection()

    customers = conn.execute("""
        SELECT *
        FROM customers
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        customers=customers
    )


# ============================================================
# WEEKLY
# ============================================================

@app.route("/weekly")
def weekly():

    conn = get_connection()

    customer_rows = conn.execute("""
        SELECT *
        FROM customers
        WHERE payment_type = 'Weekly'
        ORDER BY id DESC
    """).fetchall()

    customers = []

    # ========================================================
    # CHANGED:
    # Previously limited to Week 1 - Week 10.
    # Now the highest week is taken from the database.
    # ========================================================

    result = conn.execute("""
        SELECT COALESCE(
            MAX(p.installment_number),
            0
        )
        FROM payments p
        INNER JOIN customers c
            ON c.id = p.customer_id
        WHERE c.payment_type = 'Weekly'
    """).fetchone()

    highest_payment_week = int(
        result[0] or 0
    )

    weeks = list(
        range(
            1,
            highest_payment_week + 2
        )
    )

    if not weeks:
        weeks = [1]

    weekly_totals = {
        week: 0
        for week in weeks
    }

    for customer in customer_rows:

        customer_data = dict(customer)

        customer_id = customer["id"]

        payments = conn.execute("""
            SELECT *
            FROM payments
            WHERE customer_id = ?
            ORDER BY installment_number ASC
        """, (customer_id,)).fetchall()

        customer_data["payments"] = payments

        total_paid = sum(
            float(payment["amount_paid"] or 0)
            for payment in payments
        )

        customer_data["total_paid"] = total_paid

        total_amount = float(
            customer["total_amount"] or 0
        )

        remaining_amount = max(
            total_amount - total_paid,
            0
        )

        customer_data["remaining_amount"] = remaining_amount

        if remaining_amount <= 0:

            customer_data["display_status"] = "Completed"

        else:

            customer_data["display_status"] = customer["status"]

        # ====================================================
        # CHANGED:
        # Removed the <= 10 restriction.
        # Payments can now belong to ANY week.
        # ====================================================

        for payment in payments:

            installment = int(
                payment["installment_number"]
            )

            if installment not in weekly_totals:

                weekly_totals[installment] = 0

            weekly_totals[installment] += float(
                payment["amount_paid"] or 0
            )

        customers.append(customer_data)

    # ========================================================
    # CHANGED:
    # Create Week 1 through the highest week + 1.
    # ========================================================

    highest_week = max(
        weekly_totals.keys(),
        default=1
    )

    weeks = list(
        range(
            1,
            highest_week + 2
        )
    )

    conn.close()

    return render_template(
        "weekly.html",
        customers=customers,
        weekly_totals=weekly_totals,
        weeks=weeks
    )


# ============================================================
# MONTHLY
# ============================================================

@app.route("/monthly")
def monthly():

    conn = get_connection()

    customer_rows = conn.execute("""
        SELECT *
        FROM customers
        WHERE payment_type = 'Monthly'
        ORDER BY id DESC
    """).fetchall()

    customers = []

    result = conn.execute("""
        SELECT COALESCE(
            MAX(p.installment_number),
            0
        )
        FROM payments p
        INNER JOIN customers c
            ON c.id = p.customer_id
        WHERE c.payment_type = 'Monthly'
    """).fetchone()

    highest_payment_month = int(result[0] or 0)

    months = list(
        range(
            1,
            highest_payment_month + 2
        )
    )

    if not months:
        months = [1]

    monthly_totals = {
        month: 0
        for month in months
    }

    for customer in customer_rows:

        customer_data = dict(customer)

        customer_id = customer["id"]

        payments = conn.execute("""
            SELECT *
            FROM payments
            WHERE customer_id = ?
            ORDER BY installment_number ASC
        """, (customer_id,)).fetchall()

        customer_data["payments"] = payments

        # Total paid
        total_paid = sum(
            float(payment["amount_paid"] or 0)
            for payment in payments
        )

        customer_data["total_paid"] = total_paid

        # Principal paid
        total_principal_paid = sum(
            float(payment["principal_paid"] or 0)
            for payment in payments
        )

        customer_data["total_principal_paid"] = (
            total_principal_paid
        )

        # Interest paid
        total_interest_paid = sum(
            float(payment["interest_paid"] or 0)
            for payment in payments
        )

        customer_data["total_interest_paid"] = (
            total_interest_paid
        )

        # Original amount
        amount_taken = float(
            customer["amount_taken"] or 0
        )

        # Remaining principal
        remaining_principal = max(
            amount_taken - total_principal_paid,
            0
        )

        customer_data["remaining_principal"] = (
            remaining_principal
        )

        customer_data["remaining_amount"] = (
            remaining_principal
        )

        # Fixed monthly interest from ORIGINAL amount
        interest_rate = float(
            customer["interest_rate"] or 0
        )

        monthly_interest = (
            amount_taken
            * interest_rate
            / 100
        )

        if remaining_principal <= 0:

            monthly_interest = 0

        customer_data["monthly_interest"] = (
            monthly_interest
        )

        # Payment amount is only used as optional
        # scheduled information.
        scheduled_payment = float(
            customer["payment_amount"] or 0
        )

        customer_data["scheduled_payment"] = (
            scheduled_payment
        )

        if remaining_principal <= 0:

            customer_data["display_status"] = "Completed"

        else:

            customer_data["display_status"] = customer["status"]

        # Monthly totals
        for payment in payments:

            installment = int(
                payment["installment_number"]
            )

            if installment not in monthly_totals:

                monthly_totals[installment] = 0

            monthly_totals[installment] += float(
                payment["amount_paid"] or 0
            )

        customers.append(customer_data)

    highest_month = max(
        monthly_totals.keys(),
        default=1
    )

    months = list(
        range(
            1,
            highest_month + 2
        )
    )

    conn.close()

    return render_template(
        "monthly.html",
        customers=customers,
        monthly_totals=monthly_totals,
        months=months
    )


# ============================================================
# RECORD PAYMENT
# ============================================================

@app.route(
    "/record-payment/<int:customer_id>/<int:installment_number>",
    methods=["POST"]
)
def record_payment(
    customer_id,
    installment_number
):

    conn = get_connection()

    customer = conn.execute("""
        SELECT *
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:

        conn.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(url_for("index"))

    try:

        payment_amount = float(
            request.form.get(
                "amount_paid",
                0
            )
        )

    except (ValueError, TypeError):

        conn.close()

        flash(
            "Invalid payment amount.",
            "error"
        )

        return redirect(
            request.referrer or url_for("index")
        )

    if payment_amount <= 0:

        conn.close()

        flash(
            "Payment amount must be greater than zero.",
            "error"
        )

        return redirect(
            request.referrer or url_for("index")
        )

    payment_date = datetime.now(
        INDIA_TIMEZONE
    ).strftime("%Y-%m-%d")

    payment_method = request.form.get(
        "payment_method",
        "Cash"
    )

    notes = request.form.get(
        "notes",
        ""
    )

    # ========================================================
    # MONTHLY
    # ========================================================

    if customer["payment_type"] == "Monthly":

        total_payment_entered = payment_amount

        result = conn.execute("""
            SELECT COALESCE(
                SUM(principal_paid),
                0
            )
            FROM payments
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        principal_paid_before = float(
            result[0] or 0
        )

        amount_taken = float(
            customer["amount_taken"] or 0
        )

        remaining_principal = max(
            amount_taken - principal_paid_before,
            0
        )

        if remaining_principal <= 0:

            conn.close()

            flash(
                "This customer has already completed payment.",
                "error"
            )

            return redirect(
                url_for("monthly")
            )

        interest_rate = float(
            customer["interest_rate"] or 0
        )

        monthly_interest = (
            amount_taken
            * interest_rate
            / 100
        )

        # Interest is paid first
        if total_payment_entered >= monthly_interest:

            interest_paid = monthly_interest

            principal_paid = (
                total_payment_entered
                - monthly_interest
            )

        else:

            interest_paid = total_payment_entered

            principal_paid = 0

        # Do not allow principal to exceed remaining amount
        if principal_paid > remaining_principal:

            principal_paid = remaining_principal

        actual_total_payment = (
            principal_paid
            + interest_paid
        )

        remaining_after_payment = max(
            remaining_principal
            - principal_paid,
            0
        )

        conn.execute("""
            INSERT INTO payments (
                customer_id,
                installment_number,
                payment_date,
                amount_paid,
                principal_paid,
                interest_paid,
                payment_method,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            installment_number,
            payment_date,
            actual_total_payment,
            principal_paid,
            interest_paid,
            payment_method,
            notes
        ))

        if remaining_after_payment <= 0:

            conn.execute("""
                UPDATE customers
                SET status = 'Completed'
                WHERE id = ?
            """, (customer_id,))

        else:

            conn.execute("""
                UPDATE customers
                SET status = 'Active'
                WHERE id = ?
            """, (customer_id,))

        conn.commit()
        conn.close()

        flash(
            f"Payment ₹{actual_total_payment:.2f} recorded. "
            f"Interest: ₹{interest_paid:.2f}, "
            f"Principal: ₹{principal_paid:.2f}, "
            f"Remaining Principal: ₹{remaining_after_payment:.2f}.",
            "success"
        )

        return redirect(
            url_for("monthly")
        )

    # ========================================================
    # WEEKLY
    # ========================================================

    else:

        result = conn.execute("""
            SELECT COALESCE(
                SUM(amount_paid),
                0
            )
            FROM payments
            WHERE customer_id = ?
        """, (customer_id,)).fetchone()

        total_paid = float(
            result[0] or 0
        )

        total_amount = float(
            customer["total_amount"] or 0
        )

        remaining_amount = max(
            total_amount - total_paid,
            0
        )

        if remaining_amount <= 0:

            conn.close()

            flash(
                "This customer has already completed payment.",
                "error"
            )

            return redirect(
                url_for("weekly")
            )

        actual_payment = min(
            payment_amount,
            remaining_amount
        )

        conn.execute("""
            INSERT INTO payments (
                customer_id,
                installment_number,
                payment_date,
                amount_paid,
                principal_paid,
                interest_paid,
                payment_method,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id,
            installment_number,
            payment_date,
            actual_payment,
            actual_payment,
            0,
            payment_method,
            notes
        ))

        new_total = (
            total_paid + actual_payment
        )

        if new_total >= total_amount:

            conn.execute("""
                UPDATE customers
                SET status = 'Completed'
                WHERE id = ?
            """, (customer_id,))

        else:

            conn.execute("""
                UPDATE customers
                SET status = 'Active'
                WHERE id = ?
            """, (customer_id,))

        conn.commit()
        conn.close()

        flash(
            f"Payment of ₹{actual_payment:.2f} recorded successfully.",
            "success"
        )

        return redirect(
            url_for("weekly")
        )


# ============================================================
# ADD CUSTOMER
# ============================================================

@app.route(
    "/add-customer",
    methods=["GET", "POST"]
)
def add_customer():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        start_date = request.form.get(
            "start_date",
            ""
        )

        payment_type = request.form.get(
            "payment_type",
            ""
        )

        try:

            amount_taken = float(
                request.form.get(
                    "amount_taken",
                    0
                )
            )

        except (ValueError, TypeError):

            amount_taken = 0

        try:

            interest_rate = float(
                request.form.get(
                    "interest_rate",
                    0
                )
            )

        except (ValueError, TypeError):

            interest_rate = 0

        payment_amount_text = request.form.get(
            "payment_amount",
            ""
        ).strip()

        if payment_amount_text:

            try:

                payment_amount = float(
                    payment_amount_text
                )

            except (ValueError, TypeError):

                payment_amount = 0

        else:

            payment_amount = 0

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not name:

            flash(
                "Customer name is required.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )

        if amount_taken <= 0:

            flash(
                "Amount taken must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )

        if interest_rate < 0:

            flash(
                "Interest rate cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )

        if not payment_type:

            flash(
                "Please select Weekly or Monthly.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )

        if payment_amount < 0:

            flash(
                "Payment amount cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )

        if not start_date:

            start_date = datetime.now(
                INDIA_TIMEZONE
            ).strftime("%Y-%m-%d")

        # ====================================================
        # MONTHLY
        # ====================================================

        if payment_type == "Monthly":

            total_amount = amount_taken

            # Optional
            if payment_amount <= 0:

                payment_amount = 0

        # ====================================================
        # WEEKLY
        # ====================================================

        else:

            if payment_amount <= 0:

                flash(
                    "Please enter the Weekly payment amount.",
                    "error"
                )

                return redirect(
                    url_for("add_customer")
                )

            interest_amount = (
                amount_taken
                * interest_rate
                / 100
            )

            total_amount = (
                amount_taken
                + interest_amount
            )

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        conn = get_connection()

        conn.execute("""
            INSERT INTO customers (
                name,
                phone,
                amount_taken,
                interest_rate,
                total_amount,
                start_date,
                payment_type,
                payment_amount,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            phone,
            amount_taken,
            interest_rate,
            total_amount,
            start_date,
            payment_type,
            payment_amount,
            "Active"
        ))

        conn.commit()
        conn.close()

        flash(
            "Customer added successfully.",
            "success"
        )

        if payment_type == "Monthly":

            return redirect(
                url_for("monthly")
            )

        return redirect(
            url_for("weekly")
        )

    return render_template(
        "add_customer.html"
    )


# ============================================================
# PAYMENT HISTORY
# ============================================================

@app.route(
    "/payment-history/<int:customer_id>"
)
def payment_history(customer_id):

    conn = get_connection()

    customer = conn.execute("""
        SELECT *
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:

        conn.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    payments = conn.execute("""
        SELECT *
        FROM payments
        WHERE customer_id = ?
        ORDER BY installment_number ASC
    """, (customer_id,)).fetchall()

    total_paid = sum(
        float(payment["amount_paid"] or 0)
        for payment in payments
    )

    total_principal_paid = sum(
        float(payment["principal_paid"] or 0)
        for payment in payments
    )

    total_interest_paid = sum(
        float(payment["interest_paid"] or 0)
        for payment in payments
    )

    amount_taken = float(
        customer["amount_taken"] or 0
    )

    remaining_principal = max(
        amount_taken - total_principal_paid,
        0
    )

    interest_rate = float(
        customer["interest_rate"] or 0
    )

    if customer["payment_type"] == "Monthly":

        current_monthly_interest = (
            amount_taken
            * interest_rate
            / 100
            if remaining_principal > 0
            else 0
        )

    else:

        current_monthly_interest = (
            remaining_principal
            * interest_rate
            / 100
            if remaining_principal > 0
            else 0
        )

    conn.close()

    return render_template(
        "payment_history.html",
        customer=customer,
        payments=payments,
        total_paid=total_paid,
        total_principal_paid=total_principal_paid,
        total_interest_paid=total_interest_paid,
        remaining_principal=remaining_principal,
        current_monthly_interest=current_monthly_interest
    )


# ============================================================
# DELETE CUSTOMER
# ============================================================

@app.route(
    "/delete-customer/<int:customer_id>",
    methods=["POST"]
)
def delete_customer(customer_id):

    conn = get_connection()

    customer = conn.execute("""
        SELECT *
        FROM customers
        WHERE id = ?
    """, (customer_id,)).fetchone()

    if not customer:

        conn.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("index")
        )

    conn.execute("""
        DELETE FROM payments
        WHERE customer_id = ?
    """, (customer_id,))

    conn.execute("""
        DELETE FROM customers
        WHERE id = ?
    """, (customer_id,))

    conn.commit()
    conn.close()

    flash(
        "Customer deleted successfully.",
        "success"
    )

    if customer["payment_type"] == "Monthly":

        return redirect(
            url_for("monthly")
        )

    return redirect(
        url_for("weekly")
    )


# ============================================================
# DATABASE
# ============================================================

initialize_database()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )