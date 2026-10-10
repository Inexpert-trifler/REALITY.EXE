from app.services.verification_service import classify_result, VerificationOutcome

out = classify_result(True, True, 0.9, [])
print("Outcome:", out)
