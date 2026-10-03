from flask import Flask, render_template, request, redirect
from database import get_connection

app = Flask(__name__)


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return render_template("index.html")


# =========================================================
# WEEKLY LEDGER
# =========================================================

@app.route("/weekly")
def weekly():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.id,
            c.name,
            c.phone,
            c.amount_taken,
            c.start_date,
            c.payment_type,
            c.payment_amount,

            COALESCE(SUM(p.amount_paid), 0) AS total_paid,

            c.amount_taken -
            COALESCE(SUM(p.amount_paid), 0) AS remaining_amount,

            COUNT(p.id) AS payment_count

        FROM customers c

        LEFT JOIN payments p
            ON c.id = p.customer_id

        WHERE c.payment_type = 'Weekly'
        AND c.status = 'Active'

        GROUP BY
            c.id,
            c.name,
            c.phone,
            c.amount_taken,
            c.start_date,
            c.payment_type,
            c.payment_amount

        ORDER BY c.id DESC
    """)

    customers = cursor.fetchall()


    # Get individual payments for every customer

    for customer in customers:

        cursor.execute("""
            SELECT
                installment_number,
                payment_date,
                amount_paid,
                payment_method,
                notes

            FROM payments

            WHERE customer_id = %s

            ORDER BY installment_number ASC
        """, (customer["id"],))

        customer["payments"] = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "weekly.html",
        customers=customers
    )


# =========================================================
# MONTHLY LEDGER
# =========================================================

@app.route("/monthly")
def monthly():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.id,
            c.name,
            c.phone,
            c.amount_taken,
            c.start_date,
            c.payment_type,
            c.payment_amount,

            COALESCE(SUM(p.amount_paid), 0) AS total_paid,

            c.amount_taken -
            COALESCE(SUM(p.amount_paid), 0) AS remaining_amount,

            COUNT(p.id) AS payment_count

        FROM customers c

        LEFT JOIN payments p
            ON c.id = p.customer_id

        WHERE c.payment_type = 'Monthly'
        AND c.status = 'Active'

        GROUP BY
            c.id,
            c.name,
            c.phone,
            c.amount_taken,
            c.start_date,
            c.payment_type,
            c.payment_amount

        ORDER BY c.id DESC
    """)

    customers = cursor.fetchall()


    # Get individual payments for every customer

    for customer in customers:

        cursor.execute("""
            SELECT
                installment_number,
                payment_date,
                amount_paid,
                payment_method,
                notes

            FROM payments

            WHERE customer_id = %s

            ORDER BY installment_number ASC
        """, (customer["id"],))

        customer["payments"] = cursor.fetchall()


    cursor.close()
    connection.close()


    return render_template(
        "monthly.html",
        customers=customers
    )


# =========================================================
# ADD CUSTOMER
# =========================================================

@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():

    # Show form

    if request.method == "GET":

        return render_template("add_customer.html")


    # Get form values

    name = request.form.get("name")

    phone = request.form.get("phone")

    amount_taken = request.form.get("amount_taken")

    start_date = request.form.get("start_date")

    payment_type = request.form.get("payment_type")

    payment_amount = request.form.get("payment_amount")


    # Validate name

    if not name:

        return "Customer name is required."


    # Validate amount

    if not amount_taken:

        return "Amount taken is required."


    # Validate starting date

    if not start_date:

        return "Starting date is required."


    # Validate payment type

    if payment_type not in ["Weekly", "Monthly"]:

        return "Please select Weekly or Monthly."


    # Validate payment amount

    if not payment_amount:

        return "Payment amount is required."


    connection = None
    cursor = None


    try:

        connection = get_connection()

        cursor = connection.cursor()


        cursor.execute("""
            INSERT INTO customers
            (
                name,
                phone,
                amount_taken,
                start_date,
                payment_type,
                payment_amount,
                status
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Active'
            )
        """, (
            name,
            phone,
            amount_taken,
            start_date,
            payment_type,
            payment_amount
        ))


        connection.commit()


    except Exception as error:

        return f"""
        <html>

        <body style="font-family:Arial;padding:40px;">

            <h2>Database Error</h2>

            <p>{error}</p>

            <br>

            <a href="/add-customer">
                ← Go Back
            </a>

        </body>

        </html>
        """


    finally:

        if cursor:

            cursor.close()


        if connection:

            connection.close()


    # Redirect to correct ledger

    if payment_type == "Weekly":

        return redirect("/weekly")


    return redirect("/monthly")


# =========================================================
# ADD PAYMENT
# =========================================================

@app.route("/add-payment/<int:customer_id>", methods=["GET", "POST"])
def add_payment(customer_id):

    connection = get_connection()

    cursor = connection.cursor(dictionary=True)


    # Get customer

    cursor.execute("""
        SELECT
            id,
            name,
            amount_taken,
            payment_type,
            payment_amount

        FROM customers

        WHERE id = %s
    """, (customer_id,))


    customer = cursor.fetchone()


    if not customer:

        cursor.close()

        connection.close()

        return "Customer not found."


    # Get total paid

    cursor.execute("""
        SELECT
            COALESCE(SUM(amount_paid), 0) AS total_paid

        FROM payments

        WHERE customer_id = %s
    """, (customer_id,))


    payment_summary = cursor.fetchone()


    total_paid = float(
        payment_summary["total_paid"] or 0
    )


    # Calculate remaining

    remaining_amount = (
        float(customer["amount_taken"])
        - total_paid
    )


    # =====================================================
    # SAVE PAYMENT
    # =====================================================

    if request.method == "POST":

        payment_date = request.form.get("payment_date")

        amount_paid = request.form.get("amount_paid")

        payment_method = request.form.get("payment_method")

        notes = request.form.get("notes")


        # Validate payment date

        if not payment_date:

            cursor.close()

            connection.close()

            return "Payment date is required."


        # Validate payment amount

        if not amount_paid:

            cursor.close()

            connection.close()

            return "Payment amount is required."


        # Validate payment method

        if payment_method not in ["Cash", "Online"]:

            cursor.close()

            connection.close()

            return "Please select Cash or Online."


        # Convert amount

        try:

            amount_paid = float(amount_paid)

        except ValueError:

            cursor.close()

            connection.close()

            return "Invalid payment amount."


        # Payment must be positive

        if amount_paid <= 0:

            cursor.close()

            connection.close()

            return "Payment amount must be greater than zero."


        # Cannot pay more than remaining amount

        if amount_paid > remaining_amount:

            cursor.close()

            connection.close()

            return f"""
            <html>

            <body style="font-family:Arial;padding:40px;">

                <h2>Payment Error</h2>

                <p>
                    Payment cannot be greater than
                    the remaining amount.
                </p>

                <p>
                    Remaining amount:
                    ₹{remaining_amount:.2f}
                </p>

                <br>

                <a href="/add-payment/{customer_id}">
                    ← Go Back
                </a>

            </body>

            </html>
            """


        # =================================================
        # FIND NEXT INSTALLMENT NUMBER
        # =================================================

        cursor.execute("""
            SELECT
                COALESCE(
                    MAX(installment_number),
                    0
                ) + 1 AS next_installment

            FROM payments

            WHERE customer_id = %s
        """, (customer_id,))


        installment_data = cursor.fetchone()


        installment_number = (
            installment_data["next_installment"]
        )


        # =================================================
        # INSERT PAYMENT
        # =================================================

        cursor.execute("""
            INSERT INTO payments
            (
                customer_id,
                installment_number,
                payment_date,
                amount_paid,
                payment_method,
                notes
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            customer_id,
            installment_number,
            payment_date,
            amount_paid,
            payment_method,
            notes
        ))


        # Calculate new total

        new_total_paid = (
            total_paid + amount_paid
        )


        # Calculate new remaining

        new_remaining = (
            float(customer["amount_taken"])
            - new_total_paid
        )


        # =================================================
        # MARK CUSTOMER COMPLETED
        # =================================================

        if new_remaining <= 0:

            cursor.execute("""
                UPDATE customers

                SET status = 'Completed'

                WHERE id = %s
            """, (customer_id,))


        # Save everything

        connection.commit()


        payment_type = customer["payment_type"]


        cursor.close()

        connection.close()


        # Redirect to ledger

        if payment_type == "Weekly":

            return redirect("/weekly")


        return redirect("/monthly")


    # =====================================================
    # SHOW PAYMENT FORM
    # =====================================================

    cursor.close()

    connection.close()


    return render_template(
        "add_payment.html",
        customer=customer,
        total_paid=total_paid,
        remaining_amount=remaining_amount
    )


# =========================================================
# PAYMENT HISTORY
# =========================================================

@app.route("/payment-history/<int:customer_id>")
def payment_history(customer_id):

    connection = get_connection()

    cursor = connection.cursor(dictionary=True)


    # Get customer

    cursor.execute("""
        SELECT
            id,
            name,
            amount_taken,
            payment_type

        FROM customers

        WHERE id = %s
    """, (customer_id,))


    customer = cursor.fetchone()


    if not customer:

        cursor.close()

        connection.close()

        return "Customer not found."


    # Get payment history

    cursor.execute("""
        SELECT
            installment_number,
            payment_date,
            amount_paid,
            payment_method,
            notes

        FROM payments

        WHERE customer_id = %s

        ORDER BY installment_number ASC
    """, (customer_id,))


    payments = cursor.fetchall()


    cursor.close()

    connection.close()


    return render_template(
        "payment_history.html",
        customer=customer,
        payments=payments
    )


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route(
    "/delete-customer/<int:customer_id>",
    methods=["POST"]
)
def delete_customer(customer_id):

    connection = None

    cursor = None


    try:

        connection = get_connection()

        cursor = connection.cursor()


        # Delete customer

        # Because the database uses
        # ON DELETE CASCADE,
        # all payment records belonging
        # to this customer will also be deleted.

        cursor.execute("""
            DELETE FROM customers

            WHERE id = %s
        """, (customer_id,))


        connection.commit()


    except Exception as error:

        # Undo changes if something goes wrong

        if connection:

            connection.rollback()


        return f"""
        <html>

        <head>

            <title>Delete Error</title>

        </head>

        <body
            style="
                font-family:Arial;
                padding:40px;
                background:#fff5f8;
            "
        >

            <h2>
                Delete Error
            </h2>


            <p>
                {error}
            </p>


            <br>


            <a href="/">
                ← Back to Home
            </a>

        </body>

        </html>
        """


    finally:

        if cursor:

            cursor.close()


        if connection:

            connection.close()


    # Return to the page from which
    # the delete button was clicked

    return redirect(
        request.referrer or "/"
    )


# =========================================================
# START FLASK SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )