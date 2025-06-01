import openai
import os
import time
from typing import Optional, List, Dict, Any
from openai import OpenAIError, APIError, RateLimitError, APIConnectionError

class OpenAIService:
    """
    A comprehensive service for interacting with OpenAI's API.
    
    This class handles all aspects of communicating with OpenAI's API including:
    - Authentication and client initialization
    - Low-level API interactions with robust error handling
    - Retry logic for transient failures
    - Higher-level convenience methods for common use cases
    
    The service provides both direct access to the underlying API through 
    `create_chat_completion` for maximum flexibility, and simplified interfaces
    like `get_response` for common usage patterns.
    """
    
    def __init__(self, api_key: str):
        """Initialize the OpenAI service with your API key."""
        if not api_key:
            raise ValueError("API key cannot be empty")
        self.client = openai.Client(api_key=api_key)
    
    def create_chat_completion(
        self,
        messages: list,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[str]:
        """
        Create a chat completion using OpenAI's models with error handling.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use (defaults to gpt-3.5-turbo)
            temperature: Controls randomness (0.0 to 1.0)
            max_retries: Maximum number of retry attempts for recoverable errors
            retry_delay: Delay between retries in seconds
        
        Returns:
            The generated response text, or None if all retries failed
            
        Raises:
            ValueError: If messages are empty or malformed
            Exception: For unrecoverable API errors
        """
        if not messages:
            raise ValueError("Messages list cannot be empty")
        
        if not isinstance(messages, list):
            raise ValueError("Messages must be a list of dictionaries")
            
        for message in messages:
            if not isinstance(message, dict) or 'role' not in message or 'content' not in message:
                raise ValueError("Each message must be a dictionary with 'role' and 'content' keys")

        retries = 0
        while retries <= max_retries:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature
                )
                return response.choices[0].message.content

            except RateLimitError as e:
                if retries == max_retries:
                    print(f"Rate limit exceeded. Error: {str(e)}")
                    return None
                wait_time = retry_delay * (2 ** retries)  # Exponential backoff
                print(f"Rate limit reached. Waiting {wait_time} seconds...")
                time.sleep(wait_time)

            except APIConnectionError as e:
                if retries == max_retries:
                    print(f"Connection error: {str(e)}")
                    return None
                print(f"Connection error, retrying... ({retries + 1}/{max_retries})")
                time.sleep(retry_delay)

            except APIError as e:
                if retries == max_retries:
                    print(f"API error: {str(e)}")
                    return None
                print(f"API error, retrying... ({retries + 1}/{max_retries})")
                time.sleep(retry_delay)

            except OpenAIError as e:
                # Unrecoverable error
                print(f"OpenAI API error: {str(e)}")
                raise Exception(f"Unrecoverable error when calling OpenAI API: {str(e)}")

            except Exception as e:
                # Unexpected error
                print(f"Unexpected error: {str(e)}")
                raise

            retries += 1

        return None
    
    async def get_response(self, prompt: str) -> str:
        """
        Get a response from OpenAI for the given prompt with improved error handling.
        
        This is a simplified interface that converts a text prompt into a properly
        formatted message and handles common error scenarios with user-friendly
        messages.
        
        Args:
            prompt (str): The prompt to send to OpenAI
                
        Returns:
            str: The response from OpenAI or a user-friendly error message
        """
        print(f"Fetching OpenAI response for prompt: {prompt}")
        try:
            messages = [
                {"role": "user", "content": f"{prompt}"}
            ]
            response = self.create_chat_completion(messages)
            if response:
                print("GPT-3.5 Response:", response)
                return response
            else:
                print("Failed to get response after all retries")
                return "I couldn't generate a response at this time. Please try again later."
        except ValueError as e:
            print(f"Configuration error: {str(e)}")
            return "I'm having trouble accessing my AI services right now."
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")
            return "I encountered an error while processing your request."


def main():
    try:
        # Try to get API key from environment variable
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable")
        
        service = OpenAIService(api_key)
        
        # Example with default model (gpt-3.5-turbo)
        messages = [
            {"role": "user", "content": "What is the capital of France?"}
        ]
        
        response = service.create_chat_completion(messages)
        if response:
            print("GPT-3.5 Response:", response)
        else:
            print("Failed to get response after all retries")
        
    except ValueError as e:
        print(f"Configuration error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()