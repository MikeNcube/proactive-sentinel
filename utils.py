import re

class VRLFilter:
    @staticmethod
    def mask_pii(log_entry):
        # If we get a list of logs, mask them one by one
        if isinstance(log_entry, list):
            return [VRLFilter.mask_pii(item) for item in log_entry]
            
        # If we get a single log dictionary
        if not isinstance(log_entry, dict):
            return log_entry
            
        masked = log_entry.copy()
        
        # Mask South African ID (13 digits)
        if "id" in masked:
            masked["id"] = re.sub(r"\b\d{13}\b", "9XXXXX-XXXX-XXX", str(masked["id"]))
            
        # Mask Phone Numbers (10-12 digits)
        if "phone" in masked:
            masked["phone"] = re.sub(r"\b\d{10,12}\b", "0XX-XXX-XXXX", str(masked["phone"]))
            
        return masked
    import re

class VRLFilter:
    @staticmethod
    def mask_pii(log_entry):
        if isinstance(log_entry, list):
            return [VRLFilter.mask_pii(item) for item in log_entry]
        if not isinstance(log_entry, dict):
            return log_entry
        
        masked = log_entry.copy()
        # Mask SA ID
        if "id" in masked:
            masked["id"] = re.sub(r"\b\d{13}\b", "9XXXXX-XXXX-XXX", str(masked["id"]))
        # Mask Phone
        if "phone" in masked:
            masked["phone"] = re.sub(r"\b\d{10,12}\b", "0XX-XXX-XXXX", str(masked["phone"]))
        return masked

class ResponseSimulator:
    @staticmethod
    def isolate_user(user_id):
        print(f"[ACTION] Isolating User: {user_id} due to suspicious activity.")

    @staticmethod
    def flag_system(system_id):
        print(f"[ACTION] Flagging System: {system_id} for manual review.")

# For backward compatibility if other files call it directly
def mask_pii(log_data):
    return VRLFilter.mask_pii(log_data)