"""
Unit tests for Semantic Guardrails

Tests the 3-knot verification rule, reflection triggers, and safe-fail paths.
"""

import pytest
from src.tools.guardrails import (
    CrosswindGuardrail,
    extract_crosswind_claim_from_response,
    calculate_crosswind_component,
    parse_wind_from_string,
)


class TestWindParsing:
    """Test wind string parsing"""
    
    def test_parse_valid_wind(self):
        direction, speed = parse_wind_from_string("220 @ 10")
        assert direction == 220.0
        assert speed == 10.0
    
    def test_parse_invalid_wind(self):
        direction, speed = parse_wind_from_string("invalid")
        assert direction is None
        assert speed is None
    
    def test_parse_empty_wind(self):
        direction, speed = parse_wind_from_string("")
        assert direction is None
        assert speed is None


class TestCrosswindCalculation:
    """Test crosswind component calculations"""
    
    def test_direct_crosswind(self):
        # Wind perpendicular to runway (90° angle)
        result = calculate_crosswind_component(
            wind_speed=10.0,
            wind_direction=180.0,  # South wind
            runway_heading=270.0   # Runway 27 (west)
        )
        assert result["crosswind_kt"] == pytest.approx(10.0, abs=0.1)
        assert result["headwind_kt"] == pytest.approx(0.0, abs=0.1)
        assert result["angle_deg"] == 90.0
    
    def test_direct_headwind(self):
        # Wind directly aligned with runway
        result = calculate_crosswind_component(
            wind_speed=15.0,
            wind_direction=260.0,  # West wind
            runway_heading=260.0   # Runway 26 (west)
        )
        assert result["crosswind_kt"] == pytest.approx(0.0, abs=0.1)
        assert result["headwind_kt"] == pytest.approx(15.0, abs=0.1)
        assert result["angle_deg"] == 0.0
    
    def test_angled_wind(self):
        # 40° angle between wind and runway
        result = calculate_crosswind_component(
            wind_speed=10.0,
            wind_direction=220.0,
            runway_heading=260.0
        )
        # sin(40°) ≈ 0.643, so crosswind ≈ 10 × 0.643 = 6.43 kt
        # Using actual angle calculation (360-40=320, normalized to 40)
        assert result["crosswind_kt"] == pytest.approx(6.43, abs=0.5)
        assert result["angle_deg"] == pytest.approx(40.0, abs=1.0)


class TestClaimExtraction:
    """Test extraction of crosswind claims from agent responses"""
    
    def test_extract_simple_claim(self):
        response = "The crosswind is 5.2 knots."
        claim = extract_crosswind_claim_from_response(response)
        assert claim == 5.2
    
    def test_extract_claim_with_kt(self):
        response = "The crosswind component is 7.66 kt"
        claim = extract_crosswind_claim_from_response(response)
        assert claim == 7.66
    
    def test_extract_claim_complex_sentence(self):
        response = "At KDEN Runway 26, the crosswind component is approximately 12.5 kt."
        claim = extract_crosswind_claim_from_response(response)
        assert claim == 12.5
    
    def test_extract_no_claim(self):
        response = "Weather looks good for flying today."
        claim = extract_crosswind_claim_from_response(response)
        assert claim is None
    
    def test_extract_claim_reversed_format(self):
        response = "We have 8.3 kt crosswind today."
        claim = extract_crosswind_claim_from_response(response)
        assert claim == 8.3


class TestGuardrailVerification:
    """Test guardrail verification with 3-knot rule"""
    
    @pytest.fixture
    def guardrail(self):
        return CrosswindGuardrail(threshold_kt=3.0)
    
    @pytest.fixture
    def sample_metar(self):
        return {
            "station": "KDEN",
            "raw": "METAR KDEN 180953Z 26013KT 10SM FEW200 01/M13 A3006",
            "time": "180953Z",
            "wind": "220 @ 10",
            "wind_gust": None,
        }
    
    def test_verification_passes_accurate_claim(self, guardrail, sample_metar):
        """Test that accurate crosswind claim passes verification"""
        # Wind: 220° @ 10kt, Runway: 260° → crosswind ≈ 7.37 kt (40° angle)
        response = "The crosswind component is approximately 7.5 knots."
        
        result = guardrail.verify(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0
        )
        
        assert result["passed"] is True
        assert result["agent_claim"] == 7.5
        assert result["mathematical_truth"] == pytest.approx(7.37, abs=0.2)
        assert result["discrepancy"] < 3.0
    
    def test_verification_fails_inaccurate_claim(self, guardrail, sample_metar):
        """Test that inaccurate claim fails verification"""
        # Wind: 220° @ 10kt, Runway: 260° → crosswind ≈ 7.37 kt (40° angle)
        # Agent claims 15.5 kt (way off)
        response = "The crosswind component is approximately 15.5 knots."
        
        result = guardrail.verify(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0
        )
        
        assert result["passed"] is False
        assert result["agent_claim"] == 15.5
        assert result["mathematical_truth"] == pytest.approx(7.37, abs=0.2)
        assert result["discrepancy"] > 3.0
        assert "Crosswind discrepancy" in result["issue"]
    
    def test_verification_passes_no_claim(self, guardrail, sample_metar):
        """Test that response without crosswind claim passes"""
        response = "Weather looks good today."
        
        result = guardrail.verify(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0
        )
        
        assert result["passed"] is True
        assert result["agent_claim"] is None
    
    def test_verification_threshold_boundary(self, guardrail, sample_metar):
        """Test verification at exactly 3.0 kt threshold"""
        # Math truth ≈ 6.43 kt, claim exactly 3.0 kt away = 9.43 kt
        response = "The crosswind is 9.43 knots."
        
        result = guardrail.verify(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0
        )
        
        # Should pass at exactly threshold
        assert result["passed"] is True
        assert result["discrepancy"] <= 3.0


class TestGuardrailWithDetails:
    """Test detailed guardrail verification with tracing"""
    
    @pytest.fixture
    def guardrail(self):
        return CrosswindGuardrail(threshold_kt=3.0)
    
    @pytest.fixture
    def sample_metar(self):
        return {
            "station": "KDEN",
            "raw": "METAR KDEN 180953Z 26013KT 10SM FEW200 01/M13 A3006",
            "time": "180953Z",
            "wind": "220 @ 10",
            "wind_gust": 15,
        }
    
    def test_verify_with_details_includes_wind_data(self, guardrail, sample_metar):
        """Test that detailed verification includes wind breakdown"""
        response = "Crosswind is 6.5 kt."
        
        result = guardrail.verify_with_details(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0,
            use_gust=False
        )
        
        assert "wind_data" in result
        assert result["wind_data"]["direction"] == 220.0
        assert result["wind_data"]["speed"] == 10.0
        assert result["wind_data"]["speed_source"] == "sustained"
    
    def test_verify_with_details_uses_gust(self, guardrail, sample_metar):
        """Test that gust speed is used when enabled"""
        response = "Crosswind is 9.5 kt."
        
        result = guardrail.verify_with_details(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0,
            use_gust=True
        )
        
        assert result["wind_data"]["speed_used"] == 15.0
        assert result["wind_data"]["speed_source"] == "gust"
    
    def test_verify_with_details_includes_calculation(self, guardrail, sample_metar):
        """Test that calculation details are included"""
        response = "Crosswind is 6.5 kt."
        
        result = guardrail.verify_with_details(
            agent_response=response,
            metar_data=sample_metar,
            runway_heading=260.0
        )
        
        assert "calculation_details" in result
        calc = result["calculation_details"]
        assert "angle" in calc
        assert "formula" in calc
        assert "result" in calc
        assert calc["speed_source"] == "sustained"


class TestMagneticCorrection:
    """Test magnetic variation correction in guardrails"""
    
    @pytest.fixture
    def guardrail(self):
        return CrosswindGuardrail(threshold_kt=3.0)
    
    def test_magnetic_correction_applied(self, guardrail):
        """Test that magnetic variation is applied to wind direction"""
        metar = {
            "station": "KDEN",
            "wind": "270 @ 10",  # True west wind
            "wind_gust": None,
        }
        
        # With 7.5° east variation, magnetic wind is 270 - 7.5 = 262.5°
        result = guardrail.verify_with_details(
            agent_response="Crosswind is 0.5 kt.",
            metar_data=metar,
            runway_heading=260.0,
            magnetic_variation_deg=7.5
        )
        
        assert result["wind_data"]["direction"] == 270.0  # True
        assert result["wind_data"]["direction_magnetic"] == pytest.approx(262.5, abs=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
