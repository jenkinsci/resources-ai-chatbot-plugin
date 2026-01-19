"""
Unit tests for the data pipeline configuration loader.
"""

import os
import tempfile
import pytest
import yaml
from config.pipeline_loader import load_pipeline_config, get_phase_config, _apply_env_overrides


class TestPipelineConfigLoader:
    """Test suite for pipeline config loader."""

    @pytest.fixture
    def sample_config(self):
        """Fixture providing a minimal valid config."""
        return {
            "general": {
                "raw_data_dir": "data/raw",
                "processed_data_dir": "data/processed",
                "embeddings_dir": "data/embeddings",
                "log_level": "INFO"
            },
            "collection": {
                "docs": {
                    "base_url": "https://www.jenkins.io/doc/",
                    "output_file": "jenkins_docs.json"
                }
            },
            "preprocessing": {
                "docs": {
                    "input_file": "jenkins_docs.json",
                    "output_file": "processed_jenkins_docs.json"
                }
            },
            "chunking": {
                "chunk_size": 500,
                "chunk_overlap": 100,
                "code_block_placeholder_pattern": "\\[\\[CODE_BLOCK_(\\d+)\\]\\]",
                "placeholder_template": "[[CODE_BLOCK_{}]]",
                "docs": {
                    "input_file": "filtered_jenkins_docs.json",
                    "output_file": "chunks_docs.json",
                    "chunk_size": 500,
                    "chunk_overlap": 100
                }
            },
            "embedding": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "batch_size": 32,
                "chunk_files": ["chunks_plugin_docs.json"],
                "device": "cpu"
            },
            "storage": {
                "index_type": "IVFFlat",
                "index_file": "plugins_index.idx",
                "metadata_file": "plugins_metadata.pkl",
                "n_list": 256,
                "n_probe": 20,
                "metric": "L2"
            }
        }

    @pytest.fixture
    def temp_config_file(self, sample_config):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(sample_config, f)
            temp_path = f.name
        yield temp_path
        # Cleanup
        os.unlink(temp_path)

    def test_load_config_from_explicit_path(self, temp_config_file):
        """Test loading config from explicit path parameter."""
        config = load_pipeline_config(config_path=temp_config_file)
        assert config is not None
        assert "general" in config
        assert "chunking" in config
        assert config["chunking"]["chunk_size"] == 500

    def test_load_config_from_env_variable(self, temp_config_file, monkeypatch):
        """Test loading config from DATA_PIPELINE_CONFIG environment variable."""
        monkeypatch.setenv("DATA_PIPELINE_CONFIG", temp_config_file)
        config = load_pipeline_config()
        assert config is not None
        assert config["embedding"]["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"

    def test_load_config_missing_file(self):
        """Test that FileNotFoundError is raised for missing config file."""
        with pytest.raises(FileNotFoundError):
            load_pipeline_config(config_path="/nonexistent/config.yml")

    def test_get_phase_config(self, sample_config):
        """Test extracting specific phase configuration."""
        chunking_config = get_phase_config(sample_config, "chunking")
        assert chunking_config is not None
        assert chunking_config["chunk_size"] == 500
        assert chunking_config["chunk_overlap"] == 100

    def test_get_phase_config_invalid_phase(self, sample_config):
        """Test that KeyError is raised for invalid phase."""
        with pytest.raises(KeyError):
            get_phase_config(sample_config, "nonexistent_phase")

    def test_env_override_chunk_size(self, sample_config, monkeypatch):
        """Test environment variable override for chunk_size."""
        monkeypatch.setenv("CHUNK_SIZE", "700")
        config = _apply_env_overrides(sample_config)
        assert config["chunking"]["chunk_size"] == 700

    def test_env_override_chunk_overlap(self, sample_config, monkeypatch):
        """Test environment variable override for chunk_overlap."""
        monkeypatch.setenv("CHUNK_OVERLAP", "150")
        config = _apply_env_overrides(sample_config)
        assert config["chunking"]["chunk_overlap"] == 150

    def test_env_override_embedding_model(self, sample_config, monkeypatch):
        """Test environment variable override for embedding model."""
        monkeypatch.setenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2")
        config = _apply_env_overrides(sample_config)
        assert config["embedding"]["model_name"] == "sentence-transformers/all-mpnet-base-v2"

    def test_env_override_faiss_n_list(self, sample_config, monkeypatch):
        """Test environment variable override for FAISS n_list."""
        monkeypatch.setenv("FAISS_N_LIST", "512")
        config = _apply_env_overrides(sample_config)
        assert config["storage"]["n_list"] == 512

    def test_env_override_faiss_n_probe(self, sample_config, monkeypatch):
        """Test environment variable override for FAISS n_probe."""
        monkeypatch.setenv("FAISS_N_PROBE", "30")
        config = _apply_env_overrides(sample_config)
        assert config["storage"]["n_probe"] == 30

    def test_env_override_invalid_value(self, sample_config, monkeypatch, caplog):
        """Test that invalid environment variable values are handled gracefully."""
        monkeypatch.setenv("CHUNK_SIZE", "not_a_number")
        config = _apply_env_overrides(sample_config)
        # Should keep original value and log warning
        assert config["chunking"]["chunk_size"] == 500
        assert "Invalid CHUNK_SIZE" in caplog.text

    def test_config_structure_completeness(self, temp_config_file):
        """Test that loaded config contains all expected top-level sections."""
        config = load_pipeline_config(config_path=temp_config_file)
        expected_sections = ["general", "collection", "preprocessing", "chunking", "embedding", "storage"]
        for section in expected_sections:
            assert section in config, f"Missing config section: {section}"

    def test_chunking_per_source_configs(self, sample_config):
        """Test that per-source chunking configs are accessible."""
        chunking = get_phase_config(sample_config, "chunking")
        assert "docs" in chunking
        assert chunking["docs"]["chunk_size"] == 500
        assert chunking["docs"]["chunk_overlap"] == 100

    def test_multiple_env_overrides(self, sample_config, monkeypatch):
        """Test multiple environment variable overrides simultaneously."""
        monkeypatch.setenv("CHUNK_SIZE", "800")
        monkeypatch.setenv("CHUNK_OVERLAP", "160")
        monkeypatch.setenv("FAISS_N_LIST", "1024")
        
        config = _apply_env_overrides(sample_config)
        
        assert config["chunking"]["chunk_size"] == 800
        assert config["chunking"]["chunk_overlap"] == 160
        assert config["storage"]["n_list"] == 1024

    def test_config_immutability_of_original(self, sample_config):
        """Test that applying env overrides doesn't modify original config."""
        original_chunk_size = sample_config["chunking"]["chunk_size"]
        
        import os
        os.environ["CHUNK_SIZE"] = "999"
        _apply_env_overrides(sample_config.copy())
        
        # Original should remain unchanged if we pass a copy
        assert sample_config["chunking"]["chunk_size"] == original_chunk_size
        
        # Cleanup
        del os.environ["CHUNK_SIZE"]


class TestConfigIntegration:
    """Integration tests for config usage in pipeline scripts."""

    def test_config_paths_resolution(self):
        """Test that config paths resolve correctly relative to chatbot-core."""
        # This would test actual path resolution in the context of the project
        # Skipped in CI if chatbot-core structure not available
        pytest.skip("Requires full project structure")

    def test_config_backward_compatibility(self):
        """Test that old hard-coded defaults match new config defaults."""
        config = load_pipeline_config()
        
        # Verify defaults match previous hard-coded values
        assert config["chunking"]["chunk_size"] == 500
        assert config["chunking"]["chunk_overlap"] == 100
        assert config["embedding"]["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert config["storage"]["n_list"] == 256
        assert config["storage"]["n_probe"] == 20
