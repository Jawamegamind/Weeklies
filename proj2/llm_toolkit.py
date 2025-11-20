import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import os
import time
import platform

# Configure PyTorch for Windows stability
if platform.system() == "Windows":
    # Disable CUDA on Windows to avoid access violations
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    # Set threading to single-threaded for CPU to avoid threading issues
    torch.set_num_threads(1)
    # Disable OpenMP to prevent multi-threading issues
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["NUMEXPR_NUM_THREADS"] = "1"
    # Disable torch compile optimization which can cause issues on Windows
    os.environ["TORCH_COMPILE"] = "0"

from proj2.sqlQueries import create_connection, close_connection, fetch_one, fetch_all, execute_query


class LLM:
    """
    LLM class for local language model interactions
    """

    ## LLM parameters - prioritize MPS (Apple Silicon) > CUDA > CPU
    ## Force CPU on Windows to avoid access violation issues with transformers library
    _platform = platform.system()
    if _platform == "Windows":
        device = "cpu"
    elif torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"

    ## Set for testing - use "ibm-granite/granite-4.0-micro" or one of your choice during actual execution
    model = "ibm-granite/granite-4.0-h-350M"

    def __init__(self, tokens: int = 500):
        """
        Initializes the LLM with the specified number of tokens

        Args:
            tokens (int): The max number of generated characters
        """
        self.tokenizer = AutoTokenizer.from_pretrained(self.model, cache_dir=os.path.join(os.path.dirname(__file__), '.hf_cache'))
        
        # Load model with appropriate device configuration
        if self.device == "mps":
            # MPS (Metal Performance Shaders) for Apple Silicon
            self.model = AutoModelForCausalLM.from_pretrained(self.model, cache_dir=os.path.join(os.path.dirname(__file__), '.hf_cache'))
            self.model = self.model.to(self.device)
        elif self.device == "cuda":
            # CUDA for NVIDIA GPUs
            self.model = AutoModelForCausalLM.from_pretrained(self.model, device_map="auto")
        else:
            # CPU fallback (including Windows)
            self.model = AutoModelForCausalLM.from_pretrained(self.model, device_map=self.device)
        
        self.model.eval()
        self.tokens = tokens
        print(f"LLM initialized on device: {self.device}")


    def generate(self, context: str, prompt: str) -> str:
        """
        Uses the local LLM to generate text based on the provided context and prompt

        Args:
            context (str): The system context to provide to the LLM
            prompt (str): The user prompt to provide to the LLM  

        Returns:
            str: The raw, unformatted output from the LLM
        """
        start = time.time()
        chat = [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ]
        chat = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        # tokenize the text
        input_tokens = self.tokenizer(chat, return_tensors="pt").to(self.device)
        # generate output tokens
        output = self.model.generate(**input_tokens, 
                                    max_new_tokens=self.tokens)
        # decode output tokens into text
        output = self.tokenizer.batch_decode(output)[0]
        end = time.time()
        print("Menu Item selected in %.4f seconds" % (end - start))
        return output