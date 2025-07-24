#!/usr/bin/env python3
"""
Workflow Manager for PC Tools

Provides a cross-platform workflow management system for guided PC diagnostics
and repair workflows with RepairDesk integration.
"""

import tkinter as tk
from tkinter import ttk
import platform
import logging
from enum import Enum, auto
from typing import Dict, List, Any, Optional, Callable, Tuple, Set


class WorkflowStepStatus(Enum):
    """Status enum for workflow steps"""
    NOT_STARTED = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    ERROR = auto()
    SKIPPED = auto()


class WorkflowStep:
    """Base class for a step in a workflow"""
    
    def __init__(self, id: str, title: str, description: str = ""):
        self.id = id
        self.title = title
        self.description = description
        self.status = WorkflowStepStatus.NOT_STARTED
        self.result: Dict[str, Any] = {}
        self.parent = None
        self.step_frame = None
    
    def create_ui(self, parent) -> ttk.Frame:
        """Create the UI for this workflow step
        
        Args:
            parent: Parent frame to build UI in
            
        Returns:
            Frame containing the step UI
        """
        self.parent = parent
        self.step_frame = ttk.Frame(parent)
        
        # This is a base implementation, specific steps will override this
        ttk.Label(
            self.step_frame,
            text=self.title,
            font=("Segoe UI" if platform.system() == "Windows" else "Noto Sans", 14, "bold")
        ).pack(pady=(0, 10))
        
        ttk.Label(
            self.step_frame,
            text=self.description,
            wraplength=400
        ).pack(pady=(0, 20))
        
        return self.step_frame
    
    def enter_step(self) -> None:
        """Called when entering this step"""
        if self.status == WorkflowStepStatus.NOT_STARTED:
            self.status = WorkflowStepStatus.IN_PROGRESS
    
    def exit_step(self) -> None:
        """Called when exiting this step"""
        pass
    
    def complete_step(self, result: Dict[str, Any] = None) -> None:
        """Mark this step as completed
        
        Args:
            result: Optional results data to store
        """
        self.status = WorkflowStepStatus.COMPLETED
        if result:
            self.result.update(result)
    
    def skip_step(self) -> None:
        """Mark this step as skipped"""
        self.status = WorkflowStepStatus.SKIPPED
    
    def mark_error(self, error_msg: str) -> None:
        """Mark this step as having an error
        
        Args:
            error_msg: Error message to store
        """
        self.status = WorkflowStepStatus.ERROR
        self.result["error"] = error_msg


class Workflow:
    """Represents a complete workflow with multiple steps"""
    
    def __init__(self, id: str, title: str, description: str = ""):
        self.id = id
        self.title = title
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.current_step_index = 0
        self.result: Dict[str, Any] = {}
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to this workflow
        
        Args:
            step: The workflow step to add
        """
        self.steps.append(step)
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get the current workflow step
        
        Returns:
            Current workflow step or None if workflow is empty
        """
        if not self.steps:
            return None
            
        return self.steps[self.current_step_index]
    
    def go_to_next_step(self) -> Optional[WorkflowStep]:
        """Advance to the next step in the workflow
        
        Returns:
            Next workflow step or None if at the end
        """
        if self.current_step_index >= len(self.steps) - 1:
            # Already at the last step
            return None
            
        # Exit the current step
        current_step = self.get_current_step()
        if current_step:
            current_step.exit_step()
        
        # Advance to the next step
        self.current_step_index += 1
        next_step = self.get_current_step()
        if next_step:
            next_step.enter_step()
            
        return next_step
    
    def go_to_previous_step(self) -> Optional[WorkflowStep]:
        """Go back to the previous step in the workflow
        
        Returns:
            Previous workflow step or None if at the beginning
        """
        if self.current_step_index <= 0:
            # Already at the first step
            return None
            
        # Exit the current step
        current_step = self.get_current_step()
        if current_step:
            current_step.exit_step()
        
        # Go back to the previous step
        self.current_step_index -= 1
        prev_step = self.get_current_step()
        if prev_step:
            prev_step.enter_step()
            
        return prev_step
    
    def reset(self) -> None:
        """Reset the workflow to the beginning"""
        self.current_step_index = 0
        for step in self.steps:
            step.status = WorkflowStepStatus.NOT_STARTED
            step.result = {}
        
        # Enter the first step if any
        first_step = self.get_current_step()
        if first_step:
            first_step.enter_step()
    
    def is_complete(self) -> bool:
        """Check if the workflow is complete
        
        Returns:
            True if all steps are completed or skipped
        """
        for step in self.steps:
            if step.status not in [WorkflowStepStatus.COMPLETED, WorkflowStepStatus.SKIPPED]:
                return False
        return True
    
    def get_result(self) -> Dict[str, Any]:
        """Get the combined results from all steps
        
        Returns:
            Dictionary containing combined results
        """
        combined_result = self.result.copy()
        for step in self.steps:
            combined_result[step.id] = step.result
        return combined_result


class WorkflowManager:
    """Manages multiple workflows and provides UI integration"""
    
    def __init__(self, parent: ttk.Frame, shared_state: Dict[str, Any] = None):
        self.parent = parent
        self.shared_state = shared_state or {}
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflow: Optional[Workflow] = None
        self.ui_elements: Dict[str, Any] = {}
        
        # Get colors from RepairDesk theme
        try:
            from nest.ui.theme.colors import get_colors
            self.colors = get_colors()
        except ImportError:
            # Fallback to RepairDesk colors
            self.colors = {
                "primary": "#017E84",       # RepairDesk teal
                "primary_dark": "#016169", 
                "secondary": "#4CAF50",    
                "warning": "#FF9800",      
                "danger": "#F44336",       
                "background": "#F5F5F5",   
                "card_bg": "#FFFFFF",      
                "text_primary": "#212121", 
                "border": "#E0E0E0",       
            }
        
        # Platform-specific adjustments
        self.system = platform.system().lower()
        
        # Event callbacks
        self.on_workflow_complete: Optional[Callable[[str, Dict[str, Any]], None]] = None
        self.on_step_changed: Optional[Callable[[WorkflowStep], None]] = None
    
    def create_ui(self) -> ttk.Frame:
        """Create the workflow manager UI
        
        Returns:
            Frame containing the workflow UI
        """
        main_frame = ttk.Frame(self.parent)
        
        # Create workflow navigation header
        self.ui_elements["header"] = self._create_header(main_frame)
        self.ui_elements["header"].pack(fill="x", pady=(0, 10))
        
        # Create steps indicator
        self.ui_elements["steps_indicator"] = self._create_steps_indicator(main_frame)
        self.ui_elements["steps_indicator"].pack(fill="x", pady=(0, 15))
        
        # Create content area
        self.ui_elements["content"] = ttk.Frame(main_frame)
        self.ui_elements["content"].pack(fill="both", expand=True)
        
        # Create navigation buttons
        self.ui_elements["navigation"] = self._create_navigation(main_frame)
        self.ui_elements["navigation"].pack(fill="x", pady=(15, 0))
        
        return main_frame
    
    def _create_header(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the workflow header with title and description
        
        Args:
            parent: Parent frame
            
        Returns:
            Frame containing the header
        """
        header = ttk.Frame(parent)
        
        # Create platform-compatible font for title
        title_font = self._get_platform_font(size=16, bold=True)
        desc_font = self._get_platform_font(size=10)
        
        # Title and description
        self.ui_elements["title"] = ttk.Label(
            header,
            text="Select a workflow",
            font=title_font
        )
        self.ui_elements["title"].pack(anchor="w")
        
        self.ui_elements["description"] = ttk.Label(
            header,
            text="Choose a workflow from the list below",
            font=desc_font
        )
        self.ui_elements["description"].pack(anchor="w")
        
        return header
    
    def _create_steps_indicator(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the visual workflow steps indicator
        
        Args:
            parent: Parent frame
            
        Returns:
            Frame containing the steps indicator
        """
        frame = ttk.Frame(parent)
        self.ui_elements["steps"] = []
        
        # This will be filled dynamically when a workflow is selected
        return frame
    
    def _update_steps_indicator(self) -> None:
        """Update the steps indicator based on the active workflow"""
        # Clear existing indicators
        steps_frame = self.ui_elements["steps_indicator"]
        for widget in steps_frame.winfo_children():
            widget.destroy()
            
        self.ui_elements["steps"] = []
        
        if not self.active_workflow or not self.active_workflow.steps:
            return
            
        # Create step indicators with proper spacing
        steps = self.active_workflow.steps
        container = ttk.Frame(steps_frame)
        container.pack(fill="x")
        
        # Create indicators for each step
        for i, step in enumerate(steps):
            step_frame = ttk.Frame(container)
            step_frame.grid(row=0, column=i*2, padx=(0, 0))
            
            # Determine indicator color based on status
            color = self._get_status_color(step.status)
            
            # Create circular indicator - using a canvas for cross-platform compatibility
            indicator_size = 24
            canvas = tk.Canvas(
                step_frame, 
                width=indicator_size, 
                height=indicator_size,
                highlightthickness=0,
                background=steps_frame.cget("background") or self.colors["background"]
            )
            canvas.pack()
            
            # Draw circle
            padding = 2
            canvas.create_oval(
                padding, padding, 
                indicator_size-padding, indicator_size-padding,
                fill=color,
                outline=self.colors["border"]
            )
            
            # Add step number
            canvas.create_text(
                indicator_size/2, indicator_size/2,
                text=str(i+1),
                fill="white" if step.status != WorkflowStepStatus.NOT_STARTED else self.colors["text_primary"]
            )
            
            # Add step title below
            ttk.Label(
                step_frame,
                text=step.title,
                font=self._get_platform_font(size=9)
            ).pack()
            
            self.ui_elements["steps"].append({
                "frame": step_frame,
                "canvas": canvas,
                "step": step
            })
            
            # Add connector line between steps (except after the last step)
            if i < len(steps) - 1:
                connector = ttk.Frame(container)
                connector.grid(row=0, column=i*2+1, padx=(5, 5))
                
                # Create a simple horizontal line
                line_canvas = tk.Canvas(
                    connector,
                    width=40,
                    height=indicator_size,
                    highlightthickness=0,
                    background=steps_frame.cget("background") or self.colors["background"]
                )
                line_canvas.pack()
                
                # Draw line with appropriate color
                # If this step is complete, color the line
                line_color = self.colors["primary"] if step.status == WorkflowStepStatus.COMPLETED else self.colors["border"]
                line_canvas.create_line(
                    0, indicator_size/2,
                    40, indicator_size/2,
                    fill=line_color,
                    width=2
                )
    
    def _create_navigation(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the workflow navigation buttons
        
        Args:
            parent: Parent frame
            
        Returns:
            Frame containing navigation buttons
        """
        frame = ttk.Frame(parent)
        
        # Button container with left and right alignment
        left_buttons = ttk.Frame(frame)
        left_buttons.pack(side="left")
        
        right_buttons = ttk.Frame(frame)
        right_buttons.pack(side="right")
        
        # Back button
        self.ui_elements["back_button"] = ttk.Button(
            left_buttons,
            text="Back",
            command=self._on_back_click,
            state="disabled"
        )
        self.ui_elements["back_button"].pack(side="left", padx=(0, 10))
        
        # Next button with RepairDesk styling
        next_style = "Primary.TButton"
        try:
            next_style = "RepairDeskPrimary.TButton"  # Try RepairDesk style
        except Exception:
            pass
            
        self.ui_elements["next_button"] = ttk.Button(
            right_buttons,
            text="Next",
            command=self._on_next_click,
            style=next_style,
            state="disabled"
        )
        self.ui_elements["next_button"].pack(side="right")
        
        # Skip button if needed
        self.ui_elements["skip_button"] = ttk.Button(
            right_buttons,
            text="Skip",
            command=self._on_skip_click,
            state="disabled"
        )
        self.ui_elements["skip_button"].pack(side="right", padx=(0, 10))
        
        return frame
    
    def _on_back_click(self) -> None:
        """Handle back button click"""
        if not self.active_workflow:
            return
            
        # Go to previous step
        prev_step = self.active_workflow.go_to_previous_step()
        if prev_step:
            self._show_step(prev_step)
            if self.on_step_changed:
                self.on_step_changed(prev_step)
                
        # Update UI
        self._update_navigation_buttons()
        self._update_steps_indicator()
    
    def _on_next_click(self) -> None:
        """Handle next button click"""
        if not self.active_workflow:
            return
            
        current_step = self.active_workflow.get_current_step()
        if current_step and current_step.status == WorkflowStepStatus.IN_PROGRESS:
            # Mark current step as completed
            current_step.complete_step()
            
        # Go to next step
        next_step = self.active_workflow.go_to_next_step()
        if next_step:
            self._show_step(next_step)
            if self.on_step_changed:
                self.on_step_changed(next_step)
        else:
            # Workflow complete
            self._on_workflow_complete()
                
        # Update UI
        self._update_navigation_buttons()
        self._update_steps_indicator()
    
    def _on_skip_click(self) -> None:
        """Handle skip button click"""
        if not self.active_workflow:
            return
            
        current_step = self.active_workflow.get_current_step()
        if current_step:
            # Mark current step as skipped
            current_step.skip_step()
            
        # Continue as if Next was clicked
        self._on_next_click()
    
    def _on_workflow_complete(self) -> None:
        """Handle workflow completion"""
        if not self.active_workflow:
            return
            
        # Get final result
        workflow_id = self.active_workflow.id
        result = self.active_workflow.get_result()
        
        # Call completion callback if registered
        if self.on_workflow_complete:
            self.on_workflow_complete(workflow_id, result)
            
        # Show completion UI
        self._show_completion()
    
    def _show_completion(self) -> None:
        """Show workflow completion UI"""
        # Clear content area
        content = self.ui_elements["content"]
        for widget in content.winfo_children():
            widget.destroy()
            
        # Create completion frame
        completion_frame = ttk.Frame(content)
        completion_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title and message
        ttk.Label(
            completion_frame,
            text="Workflow Complete",
            font=self._get_platform_font(size=16, bold=True)
        ).pack(pady=(0, 20))
        
        ttk.Label(
            completion_frame,
            text="All steps in this workflow have been completed.",
            font=self._get_platform_font(size=12)
        ).pack(pady=(0, 30))
        
        # Actions
        actions_frame = ttk.Frame(completion_frame)
        actions_frame.pack()
        
        # Restart button
        ttk.Button(
            actions_frame,
            text="Restart Workflow",
            command=self._restart_active_workflow
        ).pack(side="left", padx=(0, 10))
        
        # View results button
        ttk.Button(
            actions_frame,
            text="View Results",
            command=self._show_results
        ).pack(side="left")
        
        # Update navigation
        self.ui_elements["back_button"].config(state="disabled")
        self.ui_elements["next_button"].config(state="disabled")
        self.ui_elements["skip_button"].config(state="disabled")
    
    def _restart_active_workflow(self) -> None:
        """Restart the active workflow"""
        if not self.active_workflow:
            return
            
        # Reset the workflow
        self.active_workflow.reset()
        
        # Show the first step
        first_step = self.active_workflow.get_current_step()
        if first_step:
            self._show_step(first_step)
            
        # Update UI
        self._update_navigation_buttons()
        self._update_steps_indicator()
    
    def _show_results(self) -> None:
        """Show workflow results"""
        if not self.active_workflow:
            return
            
        # Implementation would depend on how results should be displayed
        # For now, just log the results
        result = self.active_workflow.get_result()
        logging.info(f"Workflow results: {result}")
    
    def _show_step(self, step: WorkflowStep) -> None:
        """Show a workflow step in the content area
        
        Args:
            step: The workflow step to show
        """
        # Clear content area
        content = self.ui_elements["content"]
        for widget in content.winfo_children():
            widget.destroy()
            
        # Create step content
        step_content = step.create_ui(content)
        step_content.pack(fill="both", expand=True)
        
        # Update header
        self.ui_elements["title"].config(text=step.title)
        self.ui_elements["description"].config(text=step.description)
    
    def _update_navigation_buttons(self) -> None:
        """Update navigation button states based on current workflow state"""
        if not self.active_workflow:
            self.ui_elements["back_button"].config(state="disabled")
            self.ui_elements["next_button"].config(state="disabled")
            self.ui_elements["skip_button"].config(state="disabled")
            return
            
        # Enable/disable back button
        back_state = "normal" if self.active_workflow.current_step_index > 0 else "disabled"
        self.ui_elements["back_button"].config(state=back_state)
        
        # Enable/disable next button
        next_state = "normal" if self.active_workflow.current_step_index < len(self.active_workflow.steps) else "disabled"
        self.ui_elements["next_button"].config(state=next_state)
        
        # Enable/disable skip button based on current step
        current_step = self.active_workflow.get_current_step()
        skip_state = "normal" if current_step and current_step.status == WorkflowStepStatus.IN_PROGRESS else "disabled"
        self.ui_elements["skip_button"].config(state=skip_state)
        
        # Update next button text based on whether this is the last step
        is_last_step = self.active_workflow.current_step_index >= len(self.active_workflow.steps) - 1
        next_text = "Finish" if is_last_step else "Next"
        self.ui_elements["next_button"].config(text=next_text)
    
    def _get_status_color(self, status: WorkflowStepStatus) -> str:
        """Get color for a workflow step status
        
        Args:
            status: Workflow step status
            
        Returns:
            Color string for the given status
        """
        if status == WorkflowStepStatus.COMPLETED:
            return self.colors["secondary"]
        elif status == WorkflowStepStatus.IN_PROGRESS:
            return self.colors["primary"]
        elif status == WorkflowStepStatus.ERROR:
            return self.colors["danger"]
        elif status == WorkflowStepStatus.SKIPPED:
            return self.colors["warning"]
        else:  # NOT_STARTED
            return self.colors["border"]
    
    def _get_platform_font(self, size: int = 10, bold: bool = False) -> Tuple:
        """Get platform-appropriate font specification
        
        Args:
            size: Font size
            bold: Whether font should be bold
            
        Returns:
            Font specification tuple compatible with current platform
        """
        # Default font families by platform
        if self.system == "windows":
            families = ["Segoe UI", "Tahoma", "Arial"]
        elif self.system == "darwin":  # macOS
            families = ["SF Pro Text", "Helvetica Neue", "Helvetica"]
        else:  # Linux and others
            families = ["Noto Sans", "DejaVu Sans", "Liberation Sans", "FreeSans", "Arial"]
        
        # Try each font family until we find one that exists
        # For simplicity, we'll just use the first in our list
        font_family = families[0]
        
        # Create font specification
        weight = "bold" if bold else "normal"
        
        # Return as a tuple for tkinter
        return (font_family, size, weight)
    
    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow with the manager
        
        Args:
            workflow: The workflow to register
        """
        self.workflows[workflow.id] = workflow
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow by ID
        
        Args:
            workflow_id: ID of the workflow to activate
            
        Returns:
            True if workflow was activated, False if not found
        """
        if workflow_id not in self.workflows:
            return False
            
        # Activate the workflow
        self.active_workflow = self.workflows[workflow_id]
        self.active_workflow.reset()
        
        # Show the first step
        first_step = self.active_workflow.get_current_step()
        if first_step:
            self._show_step(first_step)
            
        # Update the UI
        self._update_steps_indicator()
        self._update_navigation_buttons()
        
        return True
    
    def get_workflow_list(self) -> List[Dict[str, str]]:
        """Get a list of available workflows
        
        Returns:
            List of dictionaries with workflow information
        """
        return [
            {"id": w.id, "title": w.title, "description": w.description}
            for w in self.workflows.values()
        ]


# Testing - when run directly
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Workflow Manager Test")
    root.geometry("800x600")
    
    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)
    
    # Create a workflow manager
    workflow_manager = WorkflowManager(main_frame)
    
    # Create a simple test workflow
    test_workflow = Workflow(
        "diagnostic",
        "System Diagnostic Workflow",
        "Diagnose system problems and provide solutions"
    )
    
    # Add some steps
    step1 = WorkflowStep(
        "collect_info",
        "Collect System Information",
        "Gather basic information about your system"
    )
    test_workflow.add_step(step1)
    
    step2 = WorkflowStep(
        "analyze",
        "Analyze System Health",
        "Check for common problems and issues"
    )
    test_workflow.add_step(step2)
    
    step3 = WorkflowStep(
        "solutions",
        "Review Solutions",
        "Review recommended solutions for identified issues"
    )
    test_workflow.add_step(step3)
    
    # Register the workflow
    workflow_manager.register_workflow(test_workflow)
    
    # Create UI
    workflow_ui = workflow_manager.create_ui()
    workflow_ui.pack(fill="both", expand=True)
    
    # Activate the test workflow
    workflow_manager.activate_workflow("diagnostic")
    
    root.mainloop()
