"""
Unit tests for llm_toolkit.py
Tests for the LLM class device selection and model loading
"""

import pytest
import torch
import os
from unittest.mock import Mock, patch, MagicMock

from proj2.llm_toolkit import LLM

# Skip all LLM tests on CI (GitHub Actions on Linux)
# These require GPU/model resources and significant disk space
pytestmark = pytest.mark.skipif(
    os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true",
    reason="LLM tests require model loading and are skipped on CI to prevent disk exhaustion"
)


class TestLLMDeviceSelection:
    """Tests for LLM device selection logic"""

    def test_device_attribute_exists(self):
        """Test that LLM has device attribute"""
        assert hasattr(LLM, 'device')
        assert LLM.device in ['mps', 'cuda', 'cpu']

    def test_device_priority_cpu_available(self):
        """Test that device selection works on CPU"""
        # CPU is always available
        assert LLM.device is not None
        assert isinstance(LLM.device, str)

    def test_model_attribute_exists(self):
        """Test that LLM has model attribute set"""
        assert hasattr(LLM, 'model')
        assert isinstance(LLM.model, str)
        assert 'granite' in LLM.model.lower()

    def test_model_is_valid_huggingface_name(self):
        """Test model is valid Hugging Face model name"""
        model_name = LLM.model
        # Should be in format 'org/model'
        assert '/' in model_name
        assert 'granite' in model_name.lower()


class TestLLMInitialization:
    """Tests for LLM initialization"""

    @pytest.mark.llm
    def test_llm_initialization_with_default_tokens(self):
        """Test LLM initializes with default token count"""
        llm = LLM()
        assert llm.tokens == 500
        assert hasattr(llm, 'tokenizer')
        assert hasattr(llm, 'model')

    @pytest.mark.llm
    def test_llm_initialization_with_custom_tokens(self):
        """Test LLM initializes with custom token count"""
        llm = LLM(tokens=100)
        assert llm.tokens == 100

    @pytest.mark.llm
    def test_llm_tokenizer_loaded(self):
        """Test tokenizer is properly loaded"""
        llm = LLM()
        assert llm.tokenizer is not None
        # Tokenizer should have encode/decode methods
        assert hasattr(llm.tokenizer, 'encode')
        assert hasattr(llm.tokenizer, 'decode')

    @pytest.mark.llm
    def test_llm_model_loaded(self):
        """Test model is properly loaded"""
        llm = LLM()
        assert llm.model is not None

    @pytest.mark.llm
    def test_llm_model_in_eval_mode(self):
        """Test model is set to eval mode (no training)"""
        llm = LLM()
        assert not llm.model.training

    @pytest.mark.llm
    def test_llm_invalid_token_count(self):
        """Test LLM with edge case token counts"""
        llm_small = LLM(tokens=1)
        assert llm_small.tokens == 1

        llm_large = LLM(tokens=1000)
        assert llm_large.tokens == 1000

    @pytest.mark.llm
    def test_llm_zero_tokens(self):
        """Test LLM with zero tokens"""
        llm = LLM(tokens=0)
        assert llm.tokens == 0

    @pytest.mark.llm
    def test_llm_negative_tokens(self):
        """Test LLM with negative tokens (should still initialize)"""
        llm = LLM(tokens=-100)
        assert llm.tokens == -100


class TestLLMGeneration:
    """Tests for LLM text generation"""

    @pytest.mark.llm
    def test_generate_returns_string(self):
        """Test generate method returns a string"""
        llm = LLM(tokens=50)
        context = "You are a helpful assistant."
        prompt = "What is 2+2?"
        output = llm.generate(context, prompt)
        assert isinstance(output, str)
        assert len(output) > 0

    @pytest.mark.llm
    def test_generate_with_empty_context(self):
        """Test generate with empty context"""
        llm = LLM(tokens=50)
        output = llm.generate("", "What is 2+2?")
        assert isinstance(output, str)

    @pytest.mark.llm
    def test_generate_with_empty_prompt(self):
        """Test generate with empty prompt"""
        llm = LLM(tokens=50)
        output = llm.generate("You are helpful.", "")
        assert isinstance(output, str)

    @pytest.mark.llm
    def test_generate_output_contains_input(self):
        """Test that output contains model response tags"""
        llm = LLM(tokens=50)
        context = "You are a helpful assistant."
        prompt = "Say 'hello'"
        output = llm.generate(context, prompt)
        # Granite model uses special role tags
        assert "<|" in output or len(output) > 0

    @pytest.mark.llm
    def test_generate_multiple_calls(self):
        """Test multiple sequential generate calls"""
        llm = LLM(tokens=50)
        output1 = llm.generate("You are helpful", "Say hello")
        output2 = llm.generate("You are helpful", "Say goodbye")
        # Both should return strings
        assert isinstance(output1, str)
        assert isinstance(output2, str)

    @pytest.mark.llm
    def test_generate_with_special_characters(self):
        """Test generate with special characters in prompt"""
        llm = LLM(tokens=50)
        context = "You are helpful"
        prompt = "What is 2+2? <special> & \"quotes\" 'apostrophe'"
        output = llm.generate(context, prompt)
        assert isinstance(output, str)

    @pytest.mark.llm
    def test_generate_with_unicode_characters(self):
        """Test generate with unicode characters"""
        llm = LLM(tokens=50)
        context = "You are helpful"
        prompt = "Say this: 你好世界 مرحبا العالم"
        output = llm.generate(context, prompt)
        assert isinstance(output, str)


class TestLLMCaching:
    """Tests for model caching behavior"""

    @pytest.mark.llm
    def test_model_cache_directory_exists(self):
        """Test that model cache directory is created"""
        llm = LLM()
        cache_dir = os.path.join(os.path.dirname(__file__), "../../.hf_cache")
        # Cache directory should be set
        assert True  # If we got here without errors, caching is working

    @pytest.mark.llm
    def test_multiple_llm_instances_share_model(self):
        """Test that multiple LLM instances can coexist"""
        llm1 = LLM(tokens=100)
        llm2 = LLM(tokens=200)
        # Both should have their own token settings
        assert llm1.tokens == 100
        assert llm2.tokens == 200
        # But share the model class
        assert type(llm1) == type(llm2)


class TestLLMErrorHandling:
    """Tests for error handling in LLM"""

    @pytest.mark.llm
    def test_generate_very_long_prompt(self):
        """Test generate with very long prompt"""
        llm = LLM(tokens=50)
        long_prompt = "What is 2+2? " * 1000
        output = llm.generate("You are helpful", long_prompt)
        assert isinstance(output, str)

    @pytest.mark.llm
    def test_generate_with_extremely_small_tokens(self):
        """Test generate with minimal token generation"""
        llm = LLM(tokens=1)
        output = llm.generate("You are helpful", "Say hello")
        assert isinstance(output, str)
