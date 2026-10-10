from pathlib import Path
from resolver.scaffolder import scaffold_component
from resolver.importer import _validate_tsx_syntax


def test_scaffold_component_custom_pins(temp_workspace):
    res = scaffold_component(
        name="CustomSensor",
        footprint="qfn16",
        pins=["VDD", "GND", "SDA", "SCL", "INT1", "INT2"],
        output_dir="./components",
        workspace_dir=temp_workspace
    )

    assert res.status == "success"
    assert res.name == "CustomSensor"
    assert res.footprint == "qfn16"
    assert res.pin_count == 6

    file_path = Path(res.file_path)
    assert file_path.is_file()

    content = file_path.read_text(encoding="utf-8")
    assert 'export const CustomSensor' in content
    assert 'footprint={props.footprint ?? "qfn16"}' in content
    assert 'pin1: "VDD"' in content
    assert 'pin3: "SDA"' in content

    # Check syntax validation passes
    is_valid, err = _validate_tsx_syntax(file_path)
    assert is_valid is True
    assert err is None


def test_scaffold_component_sot23_defaults(temp_workspace):
    res = scaffold_component(
        name="SimpleTransistor",
        footprint="sot23",
        output_dir="./components",
        workspace_dir=temp_workspace
    )

    assert res.status == "success"
    assert res.name == "SimpleTransistor"
    assert res.pin_count == 3

    file_path = Path(res.file_path)
    content = file_path.read_text(encoding="utf-8")
    assert 'pin1: "IN"' in content
    assert 'pin2: "OUT"' in content
    assert 'pin3: "GND"' in content

    is_valid, err = _validate_tsx_syntax(file_path)
    assert is_valid is True
