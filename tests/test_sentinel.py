import pytest

class TestUniversalIDMasking:
    """Validates cross-border identity masking for SADC region compliance."""

    def setup_method(self):
        from detections.vrl_filter import PIIMasker
        self.masker = PIIMasker()

    def test_zim_id_masked(self):
        text = "Client ZIM ID: 29-123456K78 on file"
        masked, report = self.masker.mask(text)
        assert "123456K78" not in masked
        assert "ZIM_ID" in report.pii_types_found
        # Prefix 29 and last 2 chars 78 visible
        assert "29-" in masked
        assert "78" in masked

    def test_zim_id_format_variants(self):
        cases = [
            "63-987654B21",
            "04-111111A99",
            "22-555555Z00",
        ]
        for zim_id in cases:
            masked, report = self.masker.mask(f"ID: {zim_id}")
            assert zim_id not in masked, f"Failed to mask {zim_id}"
            assert "ZIM_ID" in report.pii_types_found

    def test_zim_passport_masked(self):
        text = "Passport number: ZN1234567 issued Harare"
        masked, report = self.masker.mask(text)
        assert "1234567" not in masked
        assert "PASSPORT" in report.pii_types_found
        # Country code ZN retained
        assert "ZN" in masked
        # Last 2 digits retained
        assert "67" in masked

    def test_sa_passport_masked(self):
        text = "SA Passport: SA9876543 border control"
        masked, report = self.masker.mask(text)
        assert "9876543" not in masked
        assert "PASSPORT" in report.pii_types_found

    def test_botswana_passport_masked(self):
        text = "BW Passport BW789012 cross-border client"
        masked, report = self.masker.mask(text)
        assert "789012" not in masked

    def test_all_three_identity_types_in_one_log(self):
        text = (
            "Batch: SA ID 9201015000081, "
            "ZIM ID 29-123456K78, "
            "Passport ZN1234567"
        )
        masked, report = self.masker.mask(text)
        assert "9201015000081" not in masked
        assert "123456K78" not in masked
        assert "1234567" not in masked
        pii_types = set(report.pii_types_found)
        assert "SA_ID" in pii_types
        assert "ZIM_ID" in pii_types
        assert "PASSPORT" in pii_types
        assert report.total_replacements >= 3

    def test_masked_values_not_double_masked(self):
        """Already-masked text like XXXXXXX67 should not be re-processed."""
        already_masked = "ID: 29-XXXXXX78 on file"
        masked, report = self.masker.mask(already_masked)
        # Should not add extra X's or corrupt the masked value
        assert "XXXXXX78" in masked

    def test_cross_border_scenario_pipeline(self):
        """End-to-end style masking check for cross-border identity leak text."""
        raw_text = "SA ID 9201015000081 | ZIM 29-123456K78 | Passport ZN1234567"
        masked, report = self.masker.mask(raw_text)
        assert "9201015000081" not in masked
        assert "123456K78" not in masked
        assert "1234567" not in masked
        assert report.total_replacements >= 3

    def test_legitimate_codes_not_over_masked(self):
        """Short codes like HTTP status, port numbers, versions not masked."""
        text = "HTTP 200 OK, port 8443, version 2.1, error E404"
        masked, report = self.masker.mask(text)
        assert "200" in masked
        assert "8443" in masked
        assert "2.1" in masked

