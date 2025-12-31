"""
Paystack Payment Gateway Integration - Simplified
Uses Payment Entry directly (no Batch Payment DocType needed)
"""

import frappe
from frappe import _
import requests
import json
import uuid
from frappe.utils import get_url, today


# ============================================================================
# CONFIGURATION HELPERS
# ============================================================================

def get_paystack_settings():
    """Get Paystack settings from School Settings"""
    try:
        settings = frappe.get_doc("School Settings")
        
        if not settings.paystack_enabled:
            frappe.throw(_("Paystack is not enabled in School Settings"))
        
        test_secret_key = ""
        live_secret_key = ""
        
        try:
            test_secret_key = settings.get_password("paystack_test_secret_key", raise_exception=False) or ""
        except Exception:
            pass
        
        try:
            live_secret_key = settings.get_password("paystack_live_secret_key", raise_exception=False) or ""
        except Exception:
            pass
        
        return {
            "enabled": settings.paystack_enabled,
            "live_mode": settings.paystack_live_mode,
            "test_public_key": settings.paystack_test_public_key or "",
            "test_secret_key": test_secret_key,
            "live_public_key": settings.paystack_live_public_key or "",
            "live_secret_key": live_secret_key,
        }
    except Exception as e:
        frappe.log_error(f"Error fetching Paystack settings: {str(e)}")
        frappe.throw(_("Unable to load Paystack settings. Please check School Settings configuration."))


def get_paystack_credentials():
    """Get active API credentials based on mode (live/test)"""
    settings = get_paystack_settings()
    
    if settings["live_mode"]:
        public_key = settings["live_public_key"]
        secret_key = settings["live_secret_key"]
    else:
        public_key = settings["test_public_key"]
        secret_key = settings["test_secret_key"]
    
    if not public_key or not secret_key:
        frappe.throw(_("Paystack API credentials not configured. Please set both public and secret keys in School Settings."))
    
    return {
        "public_key": public_key,
        "secret_key": secret_key,
        "live_mode": settings["live_mode"]
    }


def get_paystack_currency():
    """Get payment currency from Company settings"""
    try:
        company = frappe.db.get_default("Company")
        currency = frappe.db.get_value("Company", company, "default_currency")
        return currency or "NGN"
    except Exception:
        return "NGN"


def validate_paystack_currency(currency):
    """Validate if currency is supported by Paystack"""
    supported_currencies = ["NGN", "GHS", "ZAR", "USD"]
    
    if currency not in supported_currencies:
        frappe.throw(
            _("Paystack only supports: {0}. Current currency: {1}").format(
                ", ".join(supported_currencies), currency
            )
        )


# ============================================================================
# PAYSTACK GATEWAY CLASS
# ============================================================================

class PaystackGateway:
    """Paystack payment gateway handler"""
    
    DEFAULT_BASE_URL = "https://api.paystack.co"
    
    def __init__(self):
        """Initialize with credentials from School Settings"""
        creds = get_paystack_credentials()
        self.public_key = creds["public_key"]
        self.secret_key = creds["secret_key"]
        self.live_mode = creds["live_mode"]
        self.currency = get_paystack_currency()
        self.base_url = self.DEFAULT_BASE_URL
        validate_paystack_currency(self.currency)
    
    def initiate_payment(self, sales_invoice, amount, email):
        """Initialize payment with Paystack"""
        try:
            unique_id = str(uuid.uuid4())[:8]
            reference = f"{sales_invoice}-{unique_id}"
            
            amount_in_base_unit = int(amount * 100)
            
            payload = {
                "email": email,
                "amount": amount_in_base_unit,
                "currency": self.currency,
                "reference": reference,
                "callback_url": self._get_callback_url(sales_invoice),
                "metadata": {
                    "sales_invoice": sales_invoice,
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.base_url}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                error_msg = response.text[:100]
                frappe.log_error(f"Paystack Error {response.status_code}: {error_msg}", "Paystack API")
                return {"success": False, "message": _("Paystack error: {0}").format(response.status_code)}
            
            result = response.json()
            
            if result.get("status"):
                return {
                    "success": True,
                    "authorization_url": result["data"]["authorization_url"],
                    "access_code": result["data"]["access_code"],
                    "reference": reference
                }
            else:
                return {"success": False, "message": result.get("message", "Payment initialization failed")}
        
        except Exception as e:
            frappe.log_error(f"Payment init error: {str(e)}", "Paystack Payment")
            return {"success": False, "message": _("Failed to connect to Paystack. Please try again.")}
    
    def verify_payment(self, reference):
        """Verify payment with Paystack"""
        try:
            headers = {
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            frappe.log_error(f"Verify payment error: {str(e)}", "Paystack Verify")
            return None
    
    def _get_callback_url(self, sales_invoice):
        """Get callback URL for payment verification"""
        return get_url(f"/api/method/piamtech_frappe_education.paystack.verify_payment?sales_invoice={sales_invoice}")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@frappe.whitelist(allow_guest=False)
def initiate_payment(sales_invoice, payment_amount, email=None):
    """Initiate Paystack payment for Sales Invoice (full or partial)"""
    try:
        doc = frappe.get_doc("Sales Invoice", sales_invoice)
        doc.check_permission("read")
        
        if not email:
            email = frappe.session.user
        
        if not email or "@" not in str(email):
            frappe.throw(_("Valid email address is required"))
        
        if not payment_amount or payment_amount <= 0:
            frappe.throw(_("Payment amount must be greater than zero"))
        
        if payment_amount > doc.grand_total:
            frappe.throw(_("Payment amount cannot exceed invoice total"))
        
        gateway = PaystackGateway()
        result = gateway.initiate_payment(sales_invoice, payment_amount, email)
        
        return result
    
    except Exception as e:
        frappe.log_error(f"Payment init error: {str(e)}", "Paystack Payment")
        return {"success": False, "message": _("Payment initialization failed")}


@frappe.whitelist(allow_guest=True)
def verify_payment(sales_invoice=None, reference=None):
    """Verify payment after user returns from Paystack"""
    try:
        if not reference:
            reference = frappe.form_dict.get("trxref") or frappe.form_dict.get("reference")
        
        if not reference:
            frappe.throw(_("No payment reference provided"))
        
        if not sales_invoice:
            sales_invoice = reference.split("-")[0]
        
        gateway = PaystackGateway()
        verification = gateway.verify_payment(reference)
        
        if not verification:
            return {"success": False, "message": _("Payment verification failed")}
        
        if verification.get("status") and verification["data"].get("status") == "success":
            payment_data = verification["data"]
            
            existing_payment = frappe.db.exists("Payment Entry", {
                "reference_no": reference,
                "docstatus": 1
            })
            
            if existing_payment:
                return {
                    "success": True,
                    "message": _("Payment already processed"),
                    "payment_entry": existing_payment,
                    "reference": reference
                }
            
            payment_entry = _create_payment_entry(sales_invoice, payment_data)
            
            return {
                "success": True,
                "message": _("Payment verified and processed successfully"),
                "payment_entry": payment_entry.name,
                "reference": reference
            }
        else:
            error_msg = verification.get("data", {}).get("gateway_response", "Payment failed")
            return {"success": False, "message": error_msg, "reference": reference}
    
    except Exception as e:
        frappe.log_error(f"Verify payment error: {str(e)}", "Paystack Verify")
        return {"success": False, "message": _("Payment verification failed")}


@frappe.whitelist(allow_guest=True)
def webhook_handler():
    """Handle Paystack webhooks for successful payments"""
    try:
        data = json.loads(frappe.request.data)
        event = data.get("event")
        
        if event == "charge.success":
            payment_data = data.get("data", {})
            reference = payment_data.get("reference")
            
            metadata = payment_data.get("metadata", {})
            sales_invoice = metadata.get("sales_invoice")
            
            if not sales_invoice:
                frappe.log_error("Invalid webhook metadata", "Paystack Webhook")
                return {"status": "error", "message": "Invalid metadata"}
            
            if not frappe.db.exists("Sales Invoice", sales_invoice):
                frappe.log_error(f"Invoice not found: {sales_invoice}", "Paystack")
                return {"status": "error", "message": "Invoice not found"}
            
            existing_payment = frappe.db.exists("Payment Entry", {
                "reference_no": reference,
                "docstatus": 1
            })
            
            if existing_payment:
                return {"status": "success", "message": "Payment already processed"}
            
            try:
                payment_entry = _create_payment_entry(sales_invoice, payment_data)
                frappe.log_error(f"✓ Payment {payment_entry.name} processed via webhook", "Paystack Webhook")
                return {
                    "status": "success",
                    "message": "Payment processed",
                    "payment_entry": payment_entry.name
                }
            except Exception as e:
                frappe.log_error(f"Webhook error: {str(e)}", "Paystack Webhook")
                return {"status": "error", "message": str(e)}
        
        return {"status": "success", "message": "Webhook received"}
    
    except Exception as e:
        frappe.log_error(f"Webhook handler error: {str(e)}", "Paystack Webhook")
        return {"status": "error", "message": str(e)}


# ============================================================================
# INTERNAL HELPER FUNCTIONS
# ============================================================================

def _create_payment_entry(sales_invoice, payment_data):
    """Create Payment Entry for the payment"""
    current_user = frappe.session.user
    
    try:
        frappe.set_user("Administrator")
        
        doc = frappe.get_doc("Sales Invoice", sales_invoice)
        company = doc.company
        
        receivable_account = frappe.db.get_value("Company", company, "default_receivable_account")
        payment_account = frappe.db.get_value("Company", company, "default_bank_account")
        
        paid_amount = float(payment_data.get("amount", 0)) / 100
        
        payment_entry = frappe.new_doc("Payment Entry")
        payment_entry.update({
            "payment_type": "Receive",
            "posting_date": today(),
            "company": company,
            "party_type": "Customer",
            "party": doc.customer,
            "paid_from": receivable_account,
            "paid_to": payment_account,
            "paid_amount": paid_amount,
            "received_amount": paid_amount,
            "reference_no": payment_data.get("reference"),
            "reference_date": today(),
            "remarks": f"Paystack Payment - {doc.name}"
        })
        
        payment_entry.append("references", {
            "reference_doctype": "Sales Invoice",
            "reference_name": sales_invoice,
            "total_amount": doc.grand_total,
            "outstanding_amount": doc.outstanding_amount,
            "allocated_amount": paid_amount
        })
        
        payment_entry.flags.ignore_permissions = True
        payment_entry.insert(ignore_permissions=True)
        payment_entry.submit()
        
        frappe.db.commit()
        
        return payment_entry
    
    finally:
        frappe.set_user(current_user)