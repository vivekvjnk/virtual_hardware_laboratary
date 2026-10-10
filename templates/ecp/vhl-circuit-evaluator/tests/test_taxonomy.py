from evaluator.models import ErrorCategory
from evaluator.taxonomy import ErrorTaxonomy


def test_taxonomy_unresolved_import():
    tax = ErrorTaxonomy()
    lines = [
        "Cannot find module './components/RP2040' or its corresponding type declarations.",
        "Error: unable to resolve import '@/components/Sensor'",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.UNRESOLVED_IMPORT


def test_taxonomy_footprint_error():
    tax = ErrorTaxonomy()
    lines = [
        "No footprint specified for component: <chip name=\"U1\" />",
        "Component unnamed_resistor1 has ftype=\"simple_resistor\" but reference designator should start with R",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.FOOTPRINT_ERROR


def test_taxonomy_unrouted_port():
    tax = ErrorTaxonomy()
    lines = [
        "Port pin1 on undefined is missing a trace",
        "Error: unrouted port detected on net VCC_3V3",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.UNROUTED_PORT


def test_taxonomy_component_pin_mismatch():
    tax = ErrorTaxonomy()
    lines = [
        "Property 'pin99' does not exist on type 'ChipProps'",
        "pinLabels schema mismatch for component U2",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.COMPONENT_PIN_MISMATCH


def test_taxonomy_syntax_error():
    tax = ErrorTaxonomy()
    lines = [
        "SyntaxError: /path/circuit.tsx:12:4: Unexpected token (12:4)",
        "JSX element 'chip' has no corresponding closing tag.",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.SYNTAX_ERROR
    assert diags[0].line_number == 12


def test_taxonomy_type_error():
    tax = ErrorTaxonomy()
    lines = [
        "TS2322: Type 'string' is not assignable to type 'number'.",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 1
    assert diags[0].category == ErrorCategory.TYPE_ERROR


def test_taxonomy_build_failure():
    tax = ErrorTaxonomy()
    lines = [
        "Build completed with errors",
        "circuit build errors occurred",
    ]
    diags = tax.classify_logs(lines)
    assert len(diags) == 2
    for d in diags:
        assert d.category == ErrorCategory.BUILD_FAILURE
