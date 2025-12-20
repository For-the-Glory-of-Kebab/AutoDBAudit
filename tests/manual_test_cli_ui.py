from autodbaudit.interface.formatted_console import ConsoleRenderer
from autodbaudit.domain.change_types import SyncStats


def test_renderer():
    print("Testing ConsoleRenderer...")

    # Mock Stats
    stats = SyncStats(
        total_findings=150,
        active_issues=5,
        documented_exceptions=10,
        compliant_items=135,
        fixed_since_baseline=3,
        regressions_since_baseline=1,
        new_issues_since_baseline=2,
        exceptions_added_since_baseline=1,
        fixed_since_last=1,
        regressions_since_last=0,
        new_issues_since_last=1,
        exceptions_added_since_last=2,
        exceptions_removed_since_last=1,
        exceptions_updated_since_last=0,
        docs_added_since_last=3,
        docs_updated_since_last=1,
        docs_removed_since_last=0,
    )

    renderer = ConsoleRenderer(use_color=True)
    renderer.render_stats_card(stats)

    print("\nCheck output above for colors and correctness.")

    # Test "No Docs Activity" case
    print("\nTesting 'No Activity' case...")
    empty_stats = SyncStats(
        total_findings=100,
        active_issues=0,
        documented_exceptions=0,
        compliant_items=100,
    )
    renderer.render_stats_card(empty_stats)


if __name__ == "__main__":
    test_renderer()
