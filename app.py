from flask import Flask, request, jsonify
from flask_cors import CORS
from mysql.connector import connect, Error
import logging

app = Flask(__name__)

CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

logging.basicConfig(level=logging.DEBUG)

def get_db_connection():
    try:
        conn = connect(
            host='127.0.0.1',
            user='root',
            password='###',
            database='bloodBank'
        )
        logging.debug("Database connection established.")
        return conn
    except Error as e:
        logging.error(f"Connection error: {e}")
        return None

def close_db_connection(db, cursor=None):
    if cursor:
        cursor.close()
        logging.debug("Cursor closed.")
    if db:
        db.close()
        logging.debug("Database connection closed.")

def create_crud_routes(table_name, fields, id_field):
    endpoint = table_name.lower()

    # Get all
    def get_all():
        db = get_db_connection()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        close_db_connection(db, cursor)
        return jsonify(rows)
    get_all.__name__ = f"get_all_{endpoint}"
    app.route(f"/api/{endpoint}", methods=['GET'])(get_all)

    # Get by id
    def get_by_id(item_id):
        db = get_db_connection()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = db.cursor(dictionary=True)
        cursor.execute(f"SELECT * FROM {table_name} WHERE {id_field} = %s", (item_id,))
        row = cursor.fetchone()
        close_db_connection(db, cursor)
        return jsonify(row) if row else (jsonify({'error': 'Not found'}), 404)
    get_by_id.__name__ = f"get_{endpoint}_by_id"
    app.route(f"/api/{endpoint}/<int:item_id>", methods=['GET'])(get_by_id)

    # Create
    def create():
        data = request.get_json()
        logging.debug(f"Creating {table_name} with data: {data}")
        db = get_db_connection()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = db.cursor()
        placeholders = ', '.join(['%s'] * len(fields))
        sql = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({placeholders})"
        try:
            cursor.execute(sql, tuple(data[field] for field in fields))
            db.commit()
            new_id = cursor.lastrowid
            logging.info(f"Successfully created {table_name} with id: {new_id}")
            close_db_connection(db, cursor)
            return jsonify({'message': f'{table_name} record created', 'id': new_id}), 201
        except Error as e:
            logging.error(f"Error creating {table_name}: {e}")
            db.rollback()
            close_db_connection(db, cursor)
            return jsonify({'error': f'Failed to create {table_name}: {e}'}), 500
    create.__name__ = f"create_{endpoint}"
    app.route(f"/api/{endpoint}", methods=['POST'])(create)

    # Update
    def update(item_id):
        data = request.get_json()
        logging.debug(f"Updating {table_name} with id {item_id} and data: {data}")
        db = get_db_connection()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = db.cursor()
        set_clauses = []
        values = []
        for field, value in data.items():
            if field in fields:
                set_clauses.append(f"{field} = %s")
                values.append(value)
        if not set_clauses:
            close_db_connection(db, cursor)
            return jsonify({'message': 'No valid fields to update'}), 200
        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_field} = %s"
        values.append(item_id)
        try:
            cursor.execute(sql, tuple(values))
            db.commit()
            close_db_connection(db, cursor)
            logging.info(f"Successfully updated {table_name} with id: {item_id}")
            return jsonify({'message': f'{table_name} record updated'})
        except Error as e:
            logging.error(f"Error updating {table_name}: {e}")
            db.rollback()
            close_db_connection(db, cursor)
            return jsonify({'error': f'Failed to update {table_name}: {e}'}), 500
    update.__name__ = f"update_{endpoint}"
    app.route(f"/api/{endpoint}/<int:item_id>", methods=['PUT'])(update)

    # Delete
    def delete(item_id):
        logging.debug(f"Deleting {table_name} with id: {item_id}")
        db = get_db_connection()
        if not db:
            return jsonify({'error': 'Database connection failed'}), 500
        cursor = db.cursor()
        sql = f"DELETE FROM {table_name} WHERE {id_field} = %s"
        try:
            cursor.execute(sql, (item_id,))
            db.commit()
            logging.info(f"Successfully deleted {table_name} with id: {item_id}")
            close_db_connection(db, cursor)
            if cursor.rowcount == 0:
                return jsonify({'error': f'No {table_name} record found with ID {item_id}'}), 404
            return jsonify({'message': f'{table_name} record deleted'})
        except Error as e:
            logging.error(f"Error deleting {table_name}: {e}")
            db.rollback()
            close_db_connection(db, cursor)
            return jsonify({'error': f'Failed to delete {table_name}: {e}'}), 500
    delete.__name__ = f"delete_{endpoint}"
    app.route(f"/api/{endpoint}/<int:item_id>", methods=['DELETE'])(delete)

# --- Donor Routes ---
create_crud_routes('Donor', [
    'Name', 'DOB', 'ContactNumber', 'Address', 'BloodType', 'LastDonationDate', 'MedicalHistory'
], 'DonorID')

# --- Patient Routes ---
create_crud_routes('Patient', [
    'Name', 'DOB', 'Gender', 'ContactInformation', 'Address', 'MedicalHistory', 'BloodType'
], 'PatientID')

create_crud_routes('Hospital', [
    'HospitalName', 'Address', 'ContactInformation'
], 'HospitalID')

create_crud_routes('Employee', [
    'Name', 'ContactInformation', 'JobTitle', 'Department'
], 'EmployeeID')

create_crud_routes('BloodInventory', [
    'BloodBankID', 'BloodID', 'Quantity', 'ExpirationDate'
], 'InventoryID')

create_crud_routes('BloodRequest', [
    'PatientID', 'HospitalID', 'BloodType', 'Quantity', 'RequestDate', 'Status'
], 'RequestID')

create_crud_routes('BloodDonation', [
    'DonorID', 'BloodBankID', 'BloodID', 'DonationDate'
], 'DonationID')

create_crud_routes('BloodTransfusion', [
    'PatientID', 'BloodID', 'TransfusionDate', 'EmployeeID'
], 'TransfusionID')

create_crud_routes('Blood', [
    'BloodType', 'DonationDate', 'ExpirationDate', 'Quantity', 'Status', 'Component'
], 'BloodID')

create_crud_routes('BloodBank', [
    'BankName', 'Address', 'ContactInformation', 'OperationalHours'
], 'BloodBankID')

if __name__ == '__main__':
    app.run(debug=True)


