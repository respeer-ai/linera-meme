"""Report planned deployment steps without executing them."""

from linest.plan.upgrade_plan import UpgradePlan


class DryRunReporter:
    """Print the steps that an upgrade plan would execute."""

    def report(self, plan: UpgradePlan) -> None:
        """Print the planned steps."""
        print(f"Dry run: deploy {plan.family.name} v{plan.target_version}")
        for index, step in enumerate(plan.steps, start=1):
            print(f"  {index}. {step.description}")
