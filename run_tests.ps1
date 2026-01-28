Write-Host "Running Consolidated Dynamic Tests..."
pytest tests/integration/test_dynamic_consolidated.py -v -s
if ($LASTEXITCODE -eq 0) {
    Write-Host "All tests passed successfully!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed." -ForegroundColor Red
}
