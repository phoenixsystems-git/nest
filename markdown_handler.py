"""Module to add Markdown formatting support to the NestBot chat display"""

def add_markdown_support(app):
    """Add Markdown formatting support to the application."""
    # Store a reference to the original methods
    original_display = app.display_ai_message
    
    # We need to completely override the display_ai_message method
    # rather than trying to work around the original one
    
    # Configure text styling tags
    app.ai_chat_display.tag_configure("bold", font=("Segoe UI", 10, "bold"))
    app.ai_chat_display.tag_configure("sender", font=("Segoe UI", 10, "bold"))
    app.ai_chat_display.tag_configure("message", font=("Segoe UI", 10))
    
    def process_markdown(message):
        """Process basic Markdown formatting in messages."""
        # Find all bold text segments marked with ** **
        segments = []
        last_end = 0
        i = 0
        
        while i < len(message):
            if i < len(message) - 1 and message[i:i+2] == "**":
                # Found opening **
                start_bold = i
                # Find closing **
                end_bold = message.find("**", start_bold + 2)
                if end_bold != -1:
                    # Add normal text before the bold section
                    if start_bold > last_end:
                        segments.append((message[last_end:start_bold], None))
                    # Add bold text without the ** markers
                    bold_text = message[start_bold+2:end_bold]
                    segments.append((bold_text, "bold"))
                    # Update position and continue search
                    last_end = end_bold + 2
                    i = last_end
                    continue
            i += 1
            
        # Add any remaining text after the last bold section
        if last_end < len(message):
            segments.append((message[last_end:], None))
            
        return segments
    
    # Define an entirely new display method
    def markdown_display_ai_message(sender, message):
        """Display a message in the AI chat display with Markdown formatting."""
        # Skip empty messages
        if message == "":
            return
            
        # Special handling for thinking message
        if sender == "NestBot" and message == "Thinking...":
            app.ai_chat_display.config(state="normal")
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M")
            formatted_sender = f"[{timestamp}] {sender}:"
            app.ai_chat_display.insert("end", formatted_sender + "\n", "sender")
            app.ai_chat_display.insert("end", "Thinking...", "message")
            app.ai_chat_display.insert("end", "\n\n")
            app.ai_chat_display.see("end")
            app.ai_chat_display.config(state="disabled")
            return
            
        # Enable text widget for editing
        app.ai_chat_display.config(state="normal")
        
        # Add timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M")
        
        # Format sender with timestamp and apply proper styling
        formatted_sender = f"[{timestamp}] {sender}:"
        app.ai_chat_display.insert("end", formatted_sender + "\n", "sender")
        
        # Process Markdown formatting
        segments = process_markdown(message)
        
        # For NestBot messages, we have to handle them differently because
        # the original display_ai_message is also being called
        if sender == "NestBot":
            # Just process the message content, but don't display the sender
            # since the original display_ai_message already did that
            if len(segments) > 0:
                # Check if there's anything to insert before getting the tag
                if app.ai_chat_display.get("end-2c", "end") != ":\n":
                    # If we have a colon without a newline, add it
                    app.ai_chat_display.insert("end", "\n")
                    
                # If we have markdown formatting like bold text
                for text, tag in segments:
                    # Use the bold tag if specified, otherwise use message tag
                    actual_tag = tag if tag else "message"
                    app.ai_chat_display.insert("end", text, actual_tag)
            else:
                # If no markdown formatting, use message tag for the whole message
                app.ai_chat_display.insert("end", message, "message")
        else:
            # For user messages, handle normally
            if len(segments) > 0:
                # If we have markdown formatting like bold text
                for text, tag in segments:
                    # Use the bold tag if specified, otherwise use message tag
                    actual_tag = tag if tag else "message"
                    app.ai_chat_display.insert("end", text, actual_tag)
            else:
                # If no markdown formatting, use message tag for the whole message
                app.ai_chat_display.insert("end", message, "message")
        
        # Add extra newlines for readability
        app.ai_chat_display.insert("end", "\n\n")
        
        # Scroll to bottom to show newest message
        app.ai_chat_display.see("end")
        
        # Disable text widget to make it read-only again
        app.ai_chat_display.config(state="disabled")
    
    # Replace the original method with our Markdown-enabled version
    # But first, let's patch the get_ai_response method to prevent double messaging
    # Create a function to fix the duplicate message issue in get_ai_response
    original_get_ai_response = app.get_ai_response
    
    def patched_get_ai_response(self, user_message):
        """Patched version of get_ai_response that avoids duplicate messages."""
        # Get the response text from the original method but don't display it yet
        response_text = original_get_ai_response(self, user_message)
        
        # Now we need to manually display the message since we commented out
        # the display line in the original get_ai_response method
        
        # Remove the 'thinking' message first
        self.root.after(0, lambda: self.remove_thinking_message())
        
        # Display the actual response after a short delay to ensure thinking message is removed
        self.root.after(50, lambda: markdown_display_ai_message("NestBot", response_text))
        
        return response_text
    
    # Only replace the display_ai_message method - don't try to patch get_ai_response
    # This will avoid the threading issue
    app.display_ai_message = markdown_display_ai_message
    
    return app
