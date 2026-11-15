"""The badge component: status labels, variants, and reactive bindings."""

import pytest

import nsh
from nsh.testing import open


def test_badge_shows_its_label_and_test_id():
    badge = nsh.badge("Paid", test_id="status")
    with open(lambda: badge) as app:
        app.wait_for("id:status")
        assert app.shows("Paid")


@pytest.mark.parametrize(
    ("variant", "surface_class", "label_class"),
    [
        ("default", "bg-primary", "text-primary-foreground"),
        ("secondary", "bg-secondary", "text-secondary-foreground"),
        ("outline", "border-border", "text-foreground"),
        ("destructive", "bg-destructive", "text-white"),
    ],
)
def test_badge_variants_show_the_label_with_matching_colors(variant, surface_class, label_class):
    badge = nsh.badge("Status", variant=variant)
    assert surface_class in badge.props["class_"].split()
    assert label_class in badge.children[0].props["class_"].split()
    with open(lambda: badge) as app:
        assert app.shows("Status")


def test_badge_bound_label_updates():
    paid = nsh.signal(False)
    badge = nsh.badge(lambda: "Paid" if paid() else "Pending")
    with open(lambda: nsh.view(badge, nsh.button("Pay", on_press=paid.setter(True)))) as app:
        assert app.shows("Pending")
        app.press("Pay")
        app.wait_for("Paid")
        assert not app.shows("Pending")


def test_badge_custom_classes_come_after_the_variant_classes():
    badge = nsh.badge("Paid", class_="bg-muted rounded-none")
    classes = badge.props["class_"].split()
    assert classes.index("bg-primary") < classes.index("bg-muted")
    assert classes[-2:] == ["bg-muted", "rounded-none"]


def test_badge_bound_classes_stay_reactive():
    classes = nsh.signal("bg-muted")
    badge = nsh.badge("Paid", class_=classes)
    binding = badge.props["class_"]
    assert callable(binding)
    assert binding().endswith(" bg-muted")
    classes.set("bg-destructive")
    assert binding().endswith(" bg-destructive")


def test_badge_rejects_an_unknown_variant():
    with pytest.raises(ValueError, match="variant"):
        nsh.badge("Paid", variant="unknown")
