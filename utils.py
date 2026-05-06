import re


class VRLFilter:
    @staticmethod
    def mask_pii(log_entry):
        if isinstance(log_entry, list):
            return [VRLFilter.mask_pii(item) for item in log_entry]
        if not isinstance(log_entry, dict):
            return log_entry

        masked = log_entry.copy()
        if "id" in masked:
            masked["id"] = re.sub(r"\b\d{13}\b", "9XXXXX-XXXX-XXX", str(masked["id"]))
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


def mask_pii(log_data):
    return VRLFilter.mask_pii(log_data)
