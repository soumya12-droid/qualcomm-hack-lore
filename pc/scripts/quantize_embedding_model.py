"""Phase 1 — standalone QNN-targeted static quantization script for the
embedding model (EmbeddingGemma 300M ONNX export) used by embedder.py.

Not part of the live indexing pipeline — run manually/offline to produce a
quantized .onnx artifact for on-NPU inference via the QNN execution
provider.

Real deployment note: this sandbox has no QNN toolchain and no real
EmbeddingGemma ONNX export, so quantization here is validated structurally
(CLI parsing, calibration-data loading, static quantization running
end-to-end) against a tiny synthetic ONNX model in tests. Real INT8/QNN-
hardware-compatibility validation must happen on the actual QNN toolchain
on the Snapdragon PC.

Calibration data contract: --calibration-data points at a directory of
.npy files, each holding a precomputed float32 array shaped
(batch, input_dim) (or (input_dim,) for a single example) matching the
model's input tensor. Swap in a real tokenizer/preprocessing pipeline to
produce these once the actual EmbeddingGemma ONNX export is available.

Usage:
    python pc/scripts/quantize_embedding_model.py \\
        --input model.onnx --calibration-data ./calib_data --output model_qnn_int8.onnx
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import onnx
from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static


class DirectoryCalibrationDataReader(CalibrationDataReader):
    """Feeds calibration tensors loaded from .npy files in a directory to
    onnxruntime.quantization.quantize_static, one file per calibration step."""

    def __init__(self, calibration_dir, input_name, max_samples=None):
        self.input_name = input_name
        paths = sorted(Path(calibration_dir).glob("*.npy"))
        if max_samples is not None:
            paths = paths[:max_samples]
        self._arrays = [np.load(path).astype(np.float32) for path in paths]
        self._iterator = iter(self._arrays)

    def get_next(self):
        array = next(self._iterator, None)
        if array is None:
            return None
        if array.ndim == 1:
            array = array[np.newaxis, :]
        return {self.input_name: array}

    def rewind(self):
        self._iterator = iter(self._arrays)


def get_model_input_name(model_path):
    """Return the first input tensor's name from an ONNX model file. Side effects: reads model_path from disk."""
    model = onnx.load(str(model_path))
    return model.graph.input[0].name


def quantize(input_path, calibration_data_dir, output_path, max_calibration_samples=None):
    """Run QNN-targeted static INT8 quantization (QDQ format, per-tensor
    QUInt8 activations / QInt8 weights — widely supported by QNN EP kernels).

    Args:
        input_path: path to the source .onnx model (fp32).
        calibration_data_dir: directory of .npy calibration tensors (see
            module docstring for the file contract).
        output_path: where to write the quantized .onnx artifact.
        max_calibration_samples: optional cap on how many calibration files to use.

    Returns:
        The output_path, as a Path.
    Raises:
        FileNotFoundError: if input_path or calibration_data_dir don't exist.
    Side effects: reads input_path and calibration_data_dir from disk;
        writes output_path (and creates its parent directories).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    calibration_dir = Path(calibration_data_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input model not found: {input_path}")
    if not calibration_dir.is_dir():
        raise FileNotFoundError(f"Calibration data directory not found: {calibration_dir}")

    input_name = get_model_input_name(input_path)
    calibration_reader = DirectoryCalibrationDataReader(calibration_dir, input_name, max_calibration_samples)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    quantize_static(
        model_input=str(input_path),
        model_output=str(output_path),
        calibration_data_reader=calibration_reader,
        quant_format=QuantFormat.QDQ,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
    )
    return output_path


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="QNN-targeted static INT8 quantization for the embedding ONNX model."
    )
    parser.add_argument("--input", required=True, help="Path to the source .onnx model (fp32).")
    parser.add_argument("--calibration-data", required=True, help="Directory of .npy calibration tensors.")
    parser.add_argument("--output", required=True, help="Path to write the quantized .onnx artifact.")
    parser.add_argument(
        "--max-calibration-samples",
        type=int,
        default=None,
        help="Optional cap on the number of calibration files to use.",
    )
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    try:
        output_path = quantize(
            args.input, args.calibration_data, args.output, args.max_calibration_samples
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Quantized model written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
