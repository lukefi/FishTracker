"""
Batch processing CLI for FishTracker using Hydra
Copyright 2025, Norwegian Institute for Nature Research
"""

import logging
import os
from pathlib import Path

import hydra
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm

from file_handler import (
    ConfKeys,
    setConfValue,
)


@hydra.main(version_base=None, config_path="configs", config_name="default.yaml")
def batch_process(cfg: DictConfig) -> None:
    """
    Process sonar files in batch mode using Hydra configuration

    Args:
        cfg: Hydra configuration
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )
    logger = logging.getLogger(__name__)

    logger.info("Batch processing started")
    logger.info(f"Configuration:\n{OmegaConf.to_yaml(cfg)}")

    # Process input files
    input_path = Path(cfg.input.path)

    input_files = []
    if input_path.is_dir():
        for ext in cfg.input.extensions:
            input_files.extend(list(input_path.glob(f"**/*{ext}")))
    else:
        input_files = [input_path]

    logger.info(f"Found {len(input_files)} files to process")
    logger.info(f"Input files:\n {[file.name for file in input_files]}")

    # Create output directory
    output_dir = Path(cfg.output.directory)
    output_dir.mkdir(exist_ok=True, parents=True)

    for file_path in tqdm(input_files, desc="Processing files"):
        process_file(file_path, cfg, output_dir)

    logger.info("Batch processing completed")


def process_file(file_path: Path, cfg: DictConfig, output_dir: Path) -> None:
    """
    Process a single sonar file

    Args:
        file_path: Path to the sonar file
        cfg: Hydra configuration
        log: Logger instance
        output_dir: Output directory path
    """
    logger = logging.getLogger(__name__)


if __name__ == "__main__":
    batch_process()
