import numpy as np
import onnx
import onnxruntime as ort
import pytest
from onnx import TensorProto, helper

from pc.scripts.quantize_embedding_model import build_arg_parser, get_model_input_name, main, quantize

INPUT_DIM = 16
EMBEDDING_DIM = 8


def _build_toy_onnx_model(path, input_dim=INPUT_DIM, embedding_dim=EMBEDDING_DIM):
    weight = np.random.RandomState(0).randn(input_dim, embedding_dim).astype(np.float32)
    weight_initializer = helper.make_tensor(
        "weight", TensorProto.FLOAT, weight.shape, weight.flatten().tolist()
    )
    input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, input_dim])
    output_tensor = helper.make_tensor_value_info("embedding", TensorProto.FLOAT, [None, embedding_dim])
    node = helper.make_node("MatMul", inputs=["input", "weight"], outputs=["embedding"])
    graph = helper.make_graph(
        [node], "toy_embedder", [input_tensor], [output_tensor], initializer=[weight_initializer]
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    onnx.checker.check_model(model)
    onnx.save(model, str(path))
    return path


@pytest.fixture
def toy_model_path(tmp_path):
    return _build_toy_onnx_model(tmp_path / "toy.onnx")


@pytest.fixture
def calibration_dir(tmp_path):
    calib_dir = tmp_path / "calib"
    calib_dir.mkdir()
    rng = np.random.RandomState(1)
    for i in range(5):
        np.save(calib_dir / f"sample_{i}.npy", rng.rand(1, INPUT_DIM).astype(np.float32))
    return calib_dir


def test_get_model_input_name(toy_model_path):
    assert get_model_input_name(toy_model_path) == "input"


def test_quantize_produces_a_working_onnx_model(toy_model_path, calibration_dir, tmp_path):
    output_path = tmp_path / "toy_int8.onnx"

    result_path = quantize(toy_model_path, calibration_dir, output_path)

    assert result_path == output_path
    assert output_path.exists()

    session = ort.InferenceSession(str(output_path), providers=["CPUExecutionProvider"])
    x = np.random.rand(2, INPUT_DIM).astype(np.float32)
    outputs = session.run(None, {"input": x})
    assert outputs[0].shape == (2, EMBEDDING_DIM)


def test_quantize_respects_max_calibration_samples(toy_model_path, calibration_dir, tmp_path):
    output_path = tmp_path / "toy_int8.onnx"
    # should not error even when capped well below the 5 available samples
    quantize(toy_model_path, calibration_dir, output_path, max_calibration_samples=2)
    assert output_path.exists()


def test_quantize_raises_for_missing_input_model(tmp_path, calibration_dir):
    with pytest.raises(FileNotFoundError):
        quantize(tmp_path / "does_not_exist.onnx", calibration_dir, tmp_path / "out.onnx")


def test_quantize_raises_for_missing_calibration_dir(toy_model_path, tmp_path):
    with pytest.raises(FileNotFoundError):
        quantize(toy_model_path, tmp_path / "no_such_calib_dir", tmp_path / "out.onnx")


def test_quantize_creates_output_parent_directories(toy_model_path, calibration_dir, tmp_path):
    output_path = tmp_path / "nested" / "dir" / "toy_int8.onnx"
    quantize(toy_model_path, calibration_dir, output_path)
    assert output_path.exists()


def test_arg_parser_requires_all_three_flags():
    parser = build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--input", "model.onnx"])


def test_arg_parser_parses_valid_args():
    parser = build_arg_parser()
    args = parser.parse_args([
        "--input", "model.onnx",
        "--calibration-data", "./calib",
        "--output", "out.onnx",
        "--max-calibration-samples", "10",
    ])
    assert args.input == "model.onnx"
    assert args.calibration_data == "./calib"
    assert args.output == "out.onnx"
    assert args.max_calibration_samples == 10


def test_main_returns_zero_on_success(toy_model_path, calibration_dir, tmp_path, capsys):
    output_path = tmp_path / "toy_int8.onnx"
    exit_code = main([
        "--input", str(toy_model_path),
        "--calibration-data", str(calibration_dir),
        "--output", str(output_path),
    ])
    assert exit_code == 0
    assert output_path.exists()
    assert "Quantized model written to" in capsys.readouterr().out


def test_main_returns_one_and_prints_error_on_missing_input(tmp_path, calibration_dir, capsys):
    exit_code = main([
        "--input", str(tmp_path / "missing.onnx"),
        "--calibration-data", str(calibration_dir),
        "--output", str(tmp_path / "out.onnx"),
    ])
    assert exit_code == 1
    assert "error:" in capsys.readouterr().err
