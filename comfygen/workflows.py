"""Workflow manipulation and management utilities."""

import json
import random
from pathlib import Path
from typing import Any, Dict, Optional, List


class WorkflowManager:
    """Manager for ComfyUI workflow manipulation."""
    
    def __init__(self, workflows_dir: Optional[str] = None):
        """Initialize workflow manager.
        
        Args:
            workflows_dir: Directory containing workflow JSON files
        """
        if workflows_dir:
            self.workflows_dir = Path(workflows_dir)
        else:
            # Default to workflows/ directory in project root
            self.workflows_dir = Path(__file__).parent.parent / "workflows"
    
    def load_workflow(self, workflow_path: str) -> Optional[Dict[str, Any]]:
        """Load a workflow from JSON file.
        
        Args:
            workflow_path: Path to workflow JSON file
            
        Returns:
            Workflow dictionary or None on failure
        """
        try:
            path = Path(workflow_path)
            if not path.is_absolute():
                path = self.workflows_dir / workflow_path
            
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def save_workflow(self, workflow: Dict[str, Any], output_path: str) -> bool:
        """Save a workflow to JSON file.
        
        Args:
            workflow: Workflow dictionary
            output_path: Path to save file
            
        Returns:
            True on success, False on failure
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(workflow, f, indent=2)
            return True
        except Exception:
            return False
    
    def set_prompt(
        self,
        workflow: Dict[str, Any],
        prompt: str,
        negative_prompt: str = ""
    ) -> Dict[str, Any]:
        """Set positive and negative prompts in workflow.
        
        Args:
            workflow: Workflow dictionary
            prompt: Positive prompt text
            negative_prompt: Negative prompt text
            
        Returns:
            Modified workflow
        """
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            
            # Handle CLIPTextEncode nodes
            if class_type == "CLIPTextEncode":
                inputs = node.get("inputs", {})
                # Identify positive vs negative by looking at connected nodes or text content
                current_text = inputs.get("text", "")
                
                # Simple heuristic: if current text looks negative, use negative prompt
                negative_keywords = ["bad", "blurry", "low quality", "worst", "ugly"]
                is_negative = any(keyword in current_text.lower() for keyword in negative_keywords)
                
                if is_negative and negative_prompt:
                    inputs["text"] = negative_prompt
                elif not is_negative and prompt:
                    inputs["text"] = prompt
        
        return workflow
    
    def set_seed(
        self,
        workflow: Dict[str, Any],
        seed: int = -1
    ) -> Dict[str, Any]:
        """Set seed in workflow.
        
        Args:
            workflow: Workflow dictionary
            seed: Seed value (-1 for random)
            
        Returns:
            Modified workflow
        """
        if seed == -1:
            seed = random.randint(0, 2**32 - 1)
        
        for node_id, node in workflow.items():
            if node.get("class_type") in ["KSampler", "KSamplerAdvanced", "SamplerCustom"]:
                if "inputs" in node:
                    node["inputs"]["seed"] = seed
        
        return workflow
    
    def set_dimensions(
        self,
        workflow: Dict[str, Any],
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Dict[str, Any]:
        """Set output dimensions in workflow.
        
        Args:
            workflow: Workflow dictionary
            width: Output width in pixels
            height: Output height in pixels
            
        Returns:
            Modified workflow
        """
        for node_id, node in workflow.items():
            if node.get("class_type") == "EmptyLatentImage":
                if "inputs" in node:
                    if width is not None:
                        node["inputs"]["width"] = width
                    if height is not None:
                        node["inputs"]["height"] = height
        
        return workflow
    
    def set_sampler_params(
        self,
        workflow: Dict[str, Any],
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        sampler_name: Optional[str] = None,
        scheduler: Optional[str] = None,
        denoise: Optional[float] = None
    ) -> Dict[str, Any]:
        """Set sampler parameters in workflow.
        
        Args:
            workflow: Workflow dictionary
            steps: Number of sampling steps
            cfg: CFG scale
            sampler_name: Sampler algorithm name
            scheduler: Scheduler name
            denoise: Denoise strength (for img2img)
            
        Returns:
            Modified workflow
        """
        for node_id, node in workflow.items():
            if node.get("class_type") in ["KSampler", "KSamplerAdvanced"]:
                if "inputs" in node:
                    if steps is not None:
                        node["inputs"]["steps"] = steps
                    if cfg is not None:
                        node["inputs"]["cfg"] = cfg
                    if sampler_name is not None:
                        node["inputs"]["sampler_name"] = sampler_name
                    if scheduler is not None:
                        node["inputs"]["scheduler"] = scheduler
                    if denoise is not None:
                        node["inputs"]["denoise"] = denoise
        
        return workflow
    
    def set_checkpoint(
        self,
        workflow: Dict[str, Any],
        checkpoint_name: str
    ) -> Dict[str, Any]:
        """Set checkpoint model in workflow.
        
        Args:
            workflow: Workflow dictionary
            checkpoint_name: Checkpoint filename
            
        Returns:
            Modified workflow
        """
        for node_id, node in workflow.items():
            if node.get("class_type") == "CheckpointLoaderSimple":
                if "inputs" in node:
                    node["inputs"]["ckpt_name"] = checkpoint_name
        
        return workflow
    
    def inject_lora(
        self,
        workflow: Dict[str, Any],
        lora_name: str,
        strength_model: float = 1.0,
        strength_clip: float = 1.0
    ) -> Dict[str, Any]:
        """Inject a LoRA into workflow.
        
        Note: This is a simplified implementation. For complex multi-LoRA injection,
        see the inject_lora function in generate.py.
        
        Args:
            workflow: Workflow dictionary
            lora_name: LoRA filename
            strength_model: Model strength
            strength_clip: CLIP strength
            
        Returns:
            Modified workflow
        """
        # Find existing LoraLoader nodes and update them
        for node_id, node in workflow.items():
            if node.get("class_type") == "LoraLoader":
                if "inputs" in node:
                    node["inputs"]["lora_name"] = lora_name
                    node["inputs"]["strength_model"] = strength_model
                    node["inputs"]["strength_clip"] = strength_clip
                    return workflow
        
        # If no LoraLoader exists, this would require complex node insertion
        # For now, just return workflow unchanged
        return workflow
    
    def list_available_workflows(self) -> List[str]:
        """List available workflow files.
        
        Returns:
            List of workflow filenames
        """
        if not self.workflows_dir.exists():
            return []
        
        return [f.name for f in self.workflows_dir.glob("*.json")]
    
    def validate_workflow(
        self,
        workflow: Dict[str, Any],
        comfyui_client = None
    ) -> Dict[str, Any]:
        """Validate workflow structure and check if referenced models exist.
        
        Args:
            workflow: Workflow dictionary to validate
            comfyui_client: Optional ComfyUIClient instance for model verification
            
        Returns:
            Dictionary with validation results:
            - is_valid (bool): True if workflow is valid
            - errors (list): List of error messages
            - warnings (list): List of warning messages
            - missing_models (list): List of missing models
        """
        errors = []
        warnings = []
        missing_models = []
        
        # Basic structure validation
        if not isinstance(workflow, dict):
            errors.append("Workflow must be a dictionary")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "missing_models": missing_models
            }
        
        if not workflow:
            errors.append("Workflow is empty")
            return {
                "is_valid": False,
                "errors": errors,
                "warnings": warnings,
                "missing_models": missing_models
            }
        
        # Check for required node types
        has_sampler = False
        has_model_loader = False
        has_save_node = False
        
        for node_id, node in workflow.items():
            class_type = node.get("class_type", "")
            
            if class_type in ["KSampler", "KSamplerAdvanced", "SamplerCustom"]:
                has_sampler = True
            
            if class_type in ["CheckpointLoaderSimple", "UNETLoader"]:
                has_model_loader = True
            
            if class_type in ["SaveImage", "VHS_VideoCombine"]:
                has_save_node = True
        
        if not has_sampler:
            warnings.append("No sampler node found (KSampler, KSamplerAdvanced, SamplerCustom)")
        
        if not has_model_loader:
            warnings.append("No model loader found (CheckpointLoaderSimple, UNETLoader)")
        
        if not has_save_node:
            warnings.append("No save node found (SaveImage, VHS_VideoCombine)")
        
        # Validate model availability if client provided
        if comfyui_client:
            try:
                available_models = comfyui_client.get_available_models()
                if available_models:
                    for node_id, node in workflow.items():
                        class_type = node.get("class_type", "")
                        inputs = node.get("inputs", {})
                        
                        # Check checkpoint models
                        if class_type == "CheckpointLoaderSimple" and "ckpt_name" in inputs:
                            ckpt = inputs["ckpt_name"]
                            if "checkpoints" in available_models and ckpt not in available_models["checkpoints"]:
                                missing_models.append({"type": "checkpoint", "name": ckpt})
                        
                        # Check LoRA models
                        elif class_type == "LoraLoader" and "lora_name" in inputs:
                            lora = inputs["lora_name"]
                            if "loras" in available_models and lora not in available_models["loras"]:
                                missing_models.append({"type": "lora", "name": lora})
                        
                        # Check VAE models
                        elif class_type == "VAELoader" and "vae_name" in inputs:
                            vae = inputs["vae_name"]
                            if "vae" in available_models and vae not in available_models["vae"]:
                                missing_models.append({"type": "vae", "name": vae})
            except Exception as e:
                warnings.append(f"Failed to validate model availability: {str(e)}")
        
        # Add errors for missing models
        if missing_models:
            for model in missing_models:
                errors.append(f"Missing {model['type']}: {model['name']}")
        
        is_valid = len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "missing_models": missing_models
        }
