from .models import Persona

def get_persona_system_message(persona: Persona):
    """Generates a system message for OpenAI based on the selected persona.

    Args:
        persona (Persona): The selected Persona object.

    Returns:
        str: A system message that defines the AI's personality based on the persona.
    """
    return (
        f"You are {persona.name}, a {persona.gender} AI from {persona.country}. "
        f"You work as a {persona.role} and are known for being {persona.characteristic}. "
        f"Your area of expertise is {persona.expertise}. "
        # Add more persona-specific instructions if needed
    )