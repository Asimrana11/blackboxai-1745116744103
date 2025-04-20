import datetime
import logging
import mysql.connector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection setup (adjust parameters as needed)
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='your_user',
        password='your_password',
        database='your_database'
    )

def schedule_appointment(patient_id, doctor_id, service_id, appointment_datetime, reason, created_by):
    """
    Schedule a new appointment for a patient with a specific doctor and service.
    Validates inputs and checks for conflicts.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate input IDs exist (example queries, adjust table/column names)
        cursor.execute("SELECT COUNT(*) FROM Patients WHERE PatientID = %s", (patient_id,))
        if cursor.fetchone()[0] == 0:
            return {"success": False, "message": "Invalid patient ID."}

        cursor.execute("SELECT COUNT(*) FROM Doctors WHERE DoctorID = %s", (doctor_id,))
        if cursor.fetchone()[0] == 0:
            return {"success": False, "message": "Invalid doctor ID."}

        cursor.execute("SELECT COUNT(*) FROM Services WHERE ServiceID = %s", (service_id,))
        if cursor.fetchone()[0] == 0:
            return {"success": False, "message": "Invalid service ID."}

        # Check for appointment conflicts (example logic)
        cursor.callproc('sp_ScheduleAppointment', (patient_id, doctor_id, service_id, appointment_datetime, reason, created_by))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return result

    except Exception as e:
        logger.error(f"Error scheduling appointment: {e}")
        return {"success": False, "message": str(e)}

def update_appointment_status(appointment_id, new_status, updated_by):
    """
    Update the status of an existing appointment.
    """
    valid_statuses = ['Scheduled', 'Checked-In', 'Completed', 'Cancelled']
    if new_status not in valid_statuses:
        return {"success": False, "message": "Invalid status value."}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc('sp_UpdateAppointmentStatus', (appointment_id, new_status, updated_by))
        result = cursor.fetchone()
        conn.commit()

        # Log the action
        log_user_action(updated_by, 'UPDATE', 'Appointments', appointment_id)

        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}")
        return {"success": False, "message": str(e)}

def generate_patient_barcode(patient_id, barcode_type):
    """
    Generate a unique barcode for a patient.
    """
    valid_barcode_types = ['QR', 'Code128', 'EAN13']
    if barcode_type not in valid_barcode_types:
        return {"success": False, "message": "Invalid barcode type."}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.callproc('sp_GeneratePatientBarcode', (patient_id, barcode_type))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error generating barcode: {e}")
        return {"success": False, "message": str(e)}

def get_patient_appointments(patient_id):
    """
    Retrieve all scheduled appointments for a specific patient.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('sp_GetPatientAppointments', (patient_id,))
        # Stored procedure results handling
        for result in cursor.stored_results():
            appointments = result.fetchall()
        cursor.close()
        conn.close()
        return appointments
    except Exception as e:
        logger.error(f"Error retrieving appointments: {e}")
        return {"success": False, "message": str(e)}

def log_user_action(user_id, action_type, table_affected, record_id):
    """
    Log user actions for auditing purposes.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO AuditLogs (UserID, ActionType, TableAffected, RecordID, ActionTimestamp)
        VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (user_id, action_type, table_affected, record_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging user action: {e}")

def cancel_appointment(appointment_id, cancelled_by):
    """
    Cancel an existing appointment by updating its status and logging the action.
    """
    try:
        update_result = update_appointment_status(appointment_id, 'Cancelled', cancelled_by)
        if not update_result.get("success", True):
            return update_result

        # Log the cancellation action
        log_user_action(cancelled_by, 'UPDATE', 'Appointments', appointment_id)
        return {"success": True, "message": "Appointment cancelled successfully."}
    except Exception as e:
        logger.error(f"Error cancelling appointment: {e}")
        return {"success": False, "message": str(e)}
