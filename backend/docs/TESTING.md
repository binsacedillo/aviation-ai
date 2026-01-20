# Automated Testing Suite

## Overview
Comprehensive test suite for guardrails and agent pipeline with 32 automated tests covering:
- Unit tests for semantic guardrails (19 tests)
- Integration tests for agent + guardrails (13 tests)
- Mock AVWX integration for offline testing

## Test Results
**Status**: ✅ ALL TESTS PASSING (32/32)

## Test Structure

### Unit Tests (`test_guardrails_unit.py`) - 19 tests
**Coverage**: Semantic guardrails verification logic

#### TestWindParsing (3 tests)
- ✅ Parse valid wind strings ("220 @ 10")
- ✅ Handle invalid wind data gracefully
- ✅ Handle empty/missing wind data

#### TestCrosswindCalculation (3 tests)
- ✅ Direct crosswind (90° angle) → 10 kt wind = 10 kt crosswind
- ✅ Direct headwind (0° angle) → 15 kt wind = 0 kt crosswind, 15 kt headwind
- ✅ Angled wind (40° angle) → Trigonometric calculation

#### TestClaimExtraction (5 tests)
- ✅ Extract simple claim: "The crosswind is 5.2 knots"
- ✅ Extract with kt abbreviation: "crosswind component is 7.66 kt"
- ✅ Extract from complex sentence
- ✅ Return None when no claim present
- ✅ Handle reversed format: "8.3 kt crosswind"

#### TestGuardrailVerification (4 tests)
- ✅ Accurate claim passes (within 3-knot threshold)
- ✅ Inaccurate claim fails (exceeds 3-knot threshold)
- ✅ No claim present → passes verification
- ✅ Threshold boundary test (exactly 3.0 kt discrepancy)

#### TestGuardrailWithDetails (3 tests)
- ✅ Detailed verification includes wind breakdown
- ✅ Gust speed selection when enabled
- ✅ Calculation details (angle, formula, result)

#### TestMagneticCorrection (1 test)
- ✅ Magnetic variation applied correctly (true → magnetic heading)

### Integration Tests (`test_agent_integration.py`) - 13 tests
**Coverage**: Full agent pipeline with guardrails

#### TestAgentGuardrailIntegration (3 tests)
- ✅ Agent tracks METAR from fetch_metar tool calls
- ✅ Agent tracks runway from select_best_runway tool calls
- ✅ Agent tracks both METAR and runway together

#### TestAgentVerification (3 tests)
- ✅ Verification passes with accurate crosswind claim
- ✅ Verification fails with inaccurate claim
- ✅ Verification skipped when METAR/runway not available

#### TestAgentReflection (2 tests)
- ✅ Reflection generates corrected response (with apology + recalculation)
- ✅ Reflected response passes verification

#### TestAgentSafeFail (2 tests)
- ✅ Safe-fail generates conservative fallback response
- ✅ Safe-fail logs audit trace to logs/trace.jsonl

#### TestAgentFullPipeline (1 test)
- ✅ Full agent run with tool calls and guardrail verification

#### TestAgentStreamingWithGuardrails (2 tests)
- ✅ Streaming emits guardrail verification event
- ✅ Streaming handles reflection without safe-fail trigger

## Running Tests

### All Tests
```bash
python -m pytest tests/ -v
```

### Unit Tests Only
```bash
python -m pytest tests/test_guardrails_unit.py -v
```

### Integration Tests Only
```bash
python -m pytest tests/test_agent_integration.py -v
```

### With Coverage Report
```bash
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term
```

### Using Test Runner Script
```bash
python run_tests.py              # All tests
python run_tests.py --unit       # Unit tests only
python run_tests.py --integration # Integration tests only
python run_tests.py --coverage   # With coverage report
```

## Test Fixtures

### Shared Fixtures (`conftest.py`)
- `sample_metar_kden`: KDEN METAR data
- `sample_metar_kbdu`: KBDU METAR data
- `sample_runway_selection`: Runway selection result
- `sample_aircraft_specs`: Cessna 172 specifications

### Test-Specific Fixtures
- `guardrail`: CrosswindGuardrail instance with 3.0 kt threshold
- `agent`: FlightAssistantAgent with simulated loop (no real LLM)
- `agent_with_data`: Agent pre-loaded with METAR and runway data
- `mock_metar_*`: Mock METAR responses for offline testing

## Mock Strategy

### AVWX Mocking
Tests use mock METAR data to avoid external API dependencies:
- No internet connection required
- Deterministic test results
- Fast test execution
- Controlled test scenarios

### Tool Call Mocking
Integration tests use `unittest.mock.patch` to mock:
- `execute_tool()` calls
- Individual tool functions
- Return predictable results

## Test Coverage

### Covered Functionality
✅ Wind parsing and validation  
✅ Crosswind/headwind calculations  
✅ Claim extraction from agent responses  
✅ 3-knot guardrail verification  
✅ Magnetic variation correction  
✅ Gust vs sustained wind selection  
✅ Reflection mechanism  
✅ Safe-fail path  
✅ Audit logging  
✅ METAR/runway tracking  
✅ Agent pipeline integration  
✅ Streaming endpoints  

### Not Covered (Future Work)
- Real AVWX API integration (requires internet)
- LLM integration (Ollama/OpenAI)
- Database persistence
- Frontend integration
- Authentication/authorization
- API rate limiting

## CI/CD Integration

### GitHub Actions Workflow
See `.github/workflows/test.yml` for automated testing on:
- Every push to main
- Every pull request
- Scheduled daily runs

### Pre-commit Hook
```bash
# Install pre-commit hook
echo "python -m pytest tests/ -v" > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Debugging Failed Tests

### View Full Output
```bash
python -m pytest tests/ -v -s  # -s shows print statements
```

### Run Specific Test
```bash
python -m pytest tests/test_guardrails_unit.py::TestGuardrailVerification::test_verification_passes_accurate_claim -v
```

### Drop into Debugger on Failure
```bash
python -m pytest tests/ --pdb
```

## Test Maintenance

### Adding New Tests
1. Create test function in appropriate test class
2. Use descriptive test name: `test_<what>_<condition>_<expected>`
3. Add docstring explaining test purpose
4. Use fixtures for common setup
5. Run tests to verify: `python -m pytest tests/ -v`

### Updating Expected Values
When system behavior changes:
1. Identify affected tests
2. Recalculate expected values
3. Update assertions
4. Document why change was made
5. Re-run full test suite

## Performance

**Test Execution Time**: ~2.5 seconds for all 32 tests

Breakdown:
- Unit tests: ~0.3s (19 tests)
- Integration tests: ~2.2s (13 tests, includes agent loops)

## Dependencies

```bash
pip install pytest pytest-mock
```

Optional for coverage:
```bash
pip install pytest-cov
```

## Summary

The test suite provides comprehensive coverage of the guardrail system and agent pipeline:
- **32 automated tests** verify all critical paths
- **100% pass rate** on all tests
- **Mock AVWX** enables offline testing
- **Fast execution** (~2.5s) enables rapid iteration
- **Clear test names** make failures easy to diagnose

The suite ensures that semantic guardrails, reflection mechanism, and safe-fail path all work correctly before deployment.
