from .models import CreditTransaction, CREDIT_COSTS


def deduct(user, job):
    cost = CREDIT_COSTS.get(job.job_type, 0)
    if cost == 0:
        return True

    if user.credits < cost:
        return False

    user.credits -= cost
    user.credits_used += cost
    user.save(update_fields=['credits', 'credits_used'])

    CreditTransaction.objects.create(
        user=user,
        job=job,
        transaction_type=CreditTransaction.USE,
        amount=-cost,
        description=f"Generate artikel: {job.keyword[:80]}",
    )
    return True


def add_credits(user, amount, description='Penambahan kredit'):
    user.credits += amount
    user.save(update_fields=['credits'])

    CreditTransaction.objects.create(
        user=user,
        transaction_type=CreditTransaction.ADD,
        amount=amount,
        description=description,
    )


def refund(user, job, description='Refund'):
    cost = CREDIT_COSTS.get(job.job_type, 0)
    if cost == 0:
        return

    user.credits += cost
    user.credits_used = max(0, user.credits_used - cost)
    user.save(update_fields=['credits', 'credits_used'])

    CreditTransaction.objects.create(
        user=user,
        job=job,
        transaction_type=CreditTransaction.REFUND,
        amount=cost,
        description=description,
    )
