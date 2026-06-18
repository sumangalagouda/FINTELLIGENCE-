import os
from datetime import datetime, timedelta, timezone
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.case import Case
from app.models.transaction import Transaction
from app.models.verification import Verification
from app.models.supervisor_approval import SupervisorApproval
from app.models.investigator_note import InvestigatorNote

from app.intelligence.silent_engine import run_silent_analysis
from app.intelligence.suspicion_score import update_case_suspicion_score
from app.intelligence.fir_readiness import calculate_fir_readiness
from app.intelligence.audit_logger import log_action

app = create_app('development')

def setup_m4_test_data():
    with app.app_context():
        print("--- STARTING M4 TESTING SCRIPT ---")
        
        # 1. Setup mock user and case
        user = User.query.filter_by(email="test_m4@fintelligence.com").first()
        if not user:
            user = User(name="M4 Tester", email="test_m4@fintelligence.com", password_hash="hash", role="supervisor")
            db.session.add(user)
            db.session.commit()
            
        case = Case(title="M4 Demonstration Case", description="Testing Velocity, Pass-Through, Cash Cycling, Governance, and Reports", created_by=user.id, assigned_to=user.id)
        db.session.add(case)
        db.session.commit()
        
        print(f"\n[+] Created Case ID: {case.id}")
        
        # 2. Setup Transactions to trigger M4 Detectors
        now = datetime.now(timezone.utc)
        
        txs = [
            # Velocity Trigger (In and out within 30 mins)
            Transaction(case_id=case.id, date=now, amount=50000, type="credit", sender_account="ACC_EXTERNAL_1", receiver_account="ACC_SUSPECT", description="Inward Remittance"),
            Transaction(case_id=case.id, date=now + timedelta(minutes=15), amount=49500, type="debit", sender_account="ACC_SUSPECT", receiver_account="ACC_EXTERNAL_2", description="Immediate Outward"),
            
            # Cash Cycling Trigger (Cash in, Cash out within 24 hours)
            Transaction(case_id=case.id, date=now - timedelta(days=2), amount=25000, type="credit", sender_account="CASH", receiver_account="ACC_SUSPECT", description="Cash Deposit"),
            Transaction(case_id=case.id, date=now - timedelta(days=2) + timedelta(hours=5), amount=24000, type="debit", sender_account="ACC_SUSPECT", receiver_account="CASH", description="Cash Withdrawal ATM"),
            
            # General Pass-Through (Total Received vs Total Sent)
            Transaction(case_id=case.id, date=now - timedelta(days=5), amount=100000, type="credit", sender_account="ACC_CORP_1", receiver_account="ACC_SUSPECT", description="Bulk Credit"),
            Transaction(case_id=case.id, date=now - timedelta(days=4), amount=96000, type="debit", sender_account="ACC_SUSPECT", receiver_account="ACC_CORP_2", description="Bulk Debit"),
        ]
        db.session.bulk_save_objects(txs)
        db.session.commit()
        print(f"[+] Inserted {len(txs)} transactions designed to trigger M4 detectors.")
        
        # 3. Run Silent Engine
        print("\n[+] Running Silent Intelligence Engine...")
        run_silent_analysis("mock_statement_id", case.id)
        
        # 4. View Suspicion Score
        breakdown = update_case_suspicion_score(case.id)
        print(f"\n--- AI Suspicion Results ---")
        print(f"Risk Score: {breakdown['risk_score']} | Level: {breakdown['risk_level']}")
        for d_name, d_val in breakdown['breakdown'].items():
            print(f" -> {d_name} (Score: {d_val['score']})")
            
        # 5. Governance: Verification & Notes
        print("\n[+] Simulating Investigator Activity (Governance)")
        v = Verification(case_id=case.id, customer_contacted=True, documents_received=True, source_verified=True, completion_percentage=100.0, verified_by=user.id)
        note = InvestigatorNote(case_id=case.id, note_text="Confirmed rapid movement of funds. M4 test successful.", author_id=user.id)
        db.session.add_all([v, note])
        db.session.commit()
        log_action(case.id, "verification_updated", user.id, notes="Verification complete.")
        
        # 6. Check FIR Readiness (Pre-Approval)
        readiness = calculate_fir_readiness(case.id)
        print(f"\n--- FIR Readiness (Before Supervisor Approval) ---")
        print(f"Ready: {readiness['ready']} | Score: {readiness['fir_readiness_score']}")
        print(f"Blocking Factors: {readiness['blocking_factors']}")
        
        # 7. Supervisor Approval Gate
        print("\n[+] Simulating Supervisor Approval")
        approval = SupervisorApproval(case_id=case.id, requested_by=user.id, status='approved', approved_by=user.id, notes="Proceed to FIR.", decided_at=datetime.now(timezone.utc))
        db.session.add(approval)
        db.session.commit()
        
        # 8. Check FIR Readiness (Post-Approval)
        readiness = calculate_fir_readiness(case.id)
        print(f"\n--- FIR Readiness (After Supervisor Approval) ---")
        print(f"Ready: {readiness['ready']} | Score: {readiness['fir_readiness_score']}")
        print(f"Blocking Factors: {readiness['blocking_factors']}")
        
        print(f"\n--- DONE! You can now use Case ID '{case.id}' to test the PDF/Dossier endpoints in Postman. ---")

if __name__ == '__main__':
    setup_m4_test_data()
