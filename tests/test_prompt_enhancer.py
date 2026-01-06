"""Tests for prompt enhancement functionality."""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestPromptEnhancerAvailability:
    """Test prompt enhancer availability checks."""

    def test_is_available_without_transformers(self):
        """Test availability check when transformers is not installed."""
        with patch.dict('sys.modules', {'transformers': None}):
            # Need to reload the module to test import behavior
            import importlib
            if 'comfy_gen.prompt_enhancer' in sys.modules:
                del sys.modules['comfy_gen.prompt_enhancer']

            from comfy_gen import prompt_enhancer
            importlib.reload(prompt_enhancer)

            # Should return False when transformers not available
            assert not prompt_enhancer.is_available()

    def test_is_available_with_transformers(self):
        """Test availability check when transformers is installed."""
        # Mock transformers module
        mock_torch = MagicMock()
        mock_transformers = MagicMock()

        with patch.dict('sys.modules', {
            'torch': mock_torch,
            'transformers': mock_transformers
        }):
            import importlib
            if 'comfy_gen.prompt_enhancer' in sys.modules:
                del sys.modules['comfy_gen.prompt_enhancer']

            from comfy_gen import prompt_enhancer
            importlib.reload(prompt_enhancer)

            # Should return True when transformers available
            assert prompt_enhancer.is_available()


class TestPromptEnhancerFallback:
    """Test graceful fallback when enhancement fails."""

    def test_enhance_prompt_fallback_no_transformers(self):
        """Test that enhance_prompt returns original when transformers unavailable."""
        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', False):
            from comfy_gen.prompt_enhancer import enhance_prompt

            original = "a cat"
            result = enhance_prompt(original)

            # Should return original prompt unchanged
            assert result == original

    @patch('comfy_gen.prompt_enhancer.PromptEnhancer')
    def test_enhance_prompt_fallback_on_error(self, mock_enhancer_class):
        """Test that enhance_prompt returns original on enhancement error."""
        # Make the enhancer raise an exception
        mock_enhancer = Mock()
        mock_enhancer.enhance.side_effect = Exception("Model error")
        mock_enhancer_class.return_value = mock_enhancer

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import enhance_prompt

            original = "a cat"
            result = enhance_prompt(original)

            # Should return original prompt on error
            assert result == original


class TestPromptEnhancerCore:
    """Test core prompt enhancer functionality (with mocked models)."""

    @patch('comfy_gen.prompt_enhancer.AutoTokenizer')
    @patch('comfy_gen.prompt_enhancer.AutoModelForCausalLM')
    @patch('comfy_gen.prompt_enhancer.pipeline')
    def test_enhancer_initialization(self, mock_pipeline, mock_model_class, mock_tokenizer_class):
        """Test enhancer initialization."""
        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import PromptEnhancer

            # Create enhancer (model not loaded yet - lazy loading)
            enhancer = PromptEnhancer()

            assert enhancer.model_name == "Qwen/Qwen2.5-0.5B-Instruct"
            assert enhancer.device == "cpu"
            assert enhancer.model is None  # Not loaded yet

    @patch('comfy_gen.prompt_enhancer.AutoTokenizer')
    @patch('comfy_gen.prompt_enhancer.AutoModelForCausalLM')
    @patch('comfy_gen.prompt_enhancer.pipeline')
    def test_enhancer_lazy_loading(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test that model is lazy-loaded on first enhance call."""
        mock_tokenizer = Mock()
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.apply_chat_template = Mock(return_value="formatted prompt")
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model

        mock_pipe = Mock()
        mock_pipe.return_value = [{"generated_text": "formatted prompt\n<|im_start|>assistant\nenhanced prompt<|im_end|>"}]
        mock_pipeline_func.return_value = mock_pipe

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import PromptEnhancer

            enhancer = PromptEnhancer()

            # Model should not be loaded yet
            assert enhancer.model is None

            # First enhance call should load model
            enhancer.enhance("a cat")

            # Model should now be loaded
            assert mock_tokenizer_class.from_pretrained.called
            assert mock_model_class.from_pretrained.called
            assert mock_pipeline_func.called

    @patch('comfy_gen.prompt_enhancer.AutoTokenizer')
    @patch('comfy_gen.prompt_enhancer.AutoModelForCausalLM')
    @patch('comfy_gen.prompt_enhancer.pipeline')
    def test_enhance_with_style(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test enhancement with style parameter."""
        mock_tokenizer = Mock()
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.apply_chat_template = Mock(return_value="formatted prompt")
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model

        mock_pipe = Mock()
        mock_pipe.return_value = [{"generated_text": "formatted prompt\n<|im_start|>assistant\nphotorealistic cat<|im_end|>"}]
        mock_pipeline_func.return_value = mock_pipe

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import PromptEnhancer

            enhancer = PromptEnhancer()
            result = enhancer.enhance("a cat", style="photorealistic")

            # Should extract the enhanced prompt
            assert "cat" in result.lower()

    @patch('comfy_gen.prompt_enhancer.AutoTokenizer')
    @patch('comfy_gen.prompt_enhancer.AutoModelForCausalLM')
    @patch('comfy_gen.prompt_enhancer.pipeline')
    def test_enhance_output_cleaning(self, mock_pipeline_func, mock_model_class, mock_tokenizer_class):
        """Test that enhancement output is properly cleaned."""
        mock_tokenizer = Mock()
        mock_tokenizer.eos_token_id = 0
        mock_tokenizer.apply_chat_template = Mock(return_value="formatted prompt")
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer

        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model

        # Test with various output formats
        test_cases = [
            # Qwen format with markers
            ("formatted prompt\n<|im_start|>assistant\nenhanced text<|im_end|>", "enhanced text"),
            # With quotes
            ('formatted prompt\n<|im_start|>assistant\n"enhanced text"<|im_end|>', "enhanced text"),
            # With extra whitespace
            ("formatted prompt\n<|im_start|>assistant\n  enhanced text  <|im_end|>", "enhanced text"),
        ]

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import PromptEnhancer

            enhancer = PromptEnhancer()

            for generated_text, expected_clean in test_cases:
                mock_pipe = Mock()
                mock_pipe.return_value = [{"generated_text": generated_text}]
                mock_pipeline_func.return_value = mock_pipe
                enhancer.pipeline = mock_pipe

                result = enhancer.enhance("test")
                assert result == expected_clean


class TestPromptEnhancerAPI:
    """Test public API functions."""

    @patch('comfy_gen.prompt_enhancer.PromptEnhancer')
    def test_enhance_prompt_function(self, mock_enhancer_class):
        """Test the enhance_prompt convenience function."""
        mock_enhancer = Mock()
        mock_enhancer.enhance.return_value = "enhanced prompt"
        mock_enhancer.model_name = "Qwen/Qwen2.5-0.5B-Instruct"
        mock_enhancer_class.return_value = mock_enhancer

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import reset_enhancer

            # Reset to clean state
            reset_enhancer()

            result = enhancer.enhance("a cat", style="photorealistic")

            # Should create enhancer and call enhance
            mock_enhancer_class.assert_called()
            mock_enhancer.enhance.assert_called()
            assert result == "enhanced prompt"

    @patch('comfy_gen.prompt_enhancer.PromptEnhancer')
    def test_enhance_prompt_model_parameter(self, mock_enhancer_class):
        """Test enhance_prompt with custom model parameter."""
        mock_enhancer = Mock()
        mock_enhancer.enhance.return_value = "enhanced"
        mock_enhancer.model_name = "microsoft/phi-2"
        mock_enhancer_class.return_value = mock_enhancer

        with patch('comfy_gen.prompt_enhancer.TRANSFORMERS_AVAILABLE', True):
            from comfy_gen.prompt_enhancer import enhance_prompt, reset_enhancer

            # Reset to clean state
            reset_enhancer()

            enhance_prompt("a cat", model="microsoft/phi-2")

            # Should create enhancer with specified model
            mock_enhancer_class.assert_called_with(model_name="microsoft/phi-2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
