import asyncio
from app.database import async_session
from app.api.persona.models import Persona
from sqlalchemy.exc import IntegrityError

async def populate_personas():
    async with async_session() as db:
        personas = [
            {
                "name": "Atlas",
                "gender": "Male",
                "country": "United States",
                "language": "English",
                "role": "Secretary",
                "characteristic": "Charismatic",
                "expertise": "General"
            }
        ]

        for persona_data in personas:
            try:
                persona = Persona(**persona_data)
                print(persona)
                db.add(persona)
                await db.commit()
            except IntegrityError as e:
                print(f"Error adding persona: {e}")
                await db.rollback()  # Rollback the transaction in case of error
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                await db.rollback()

        print("Personas added to the database.")

if __name__ == "__main__":
    asyncio.run(populate_personas())