import asyncio
from database.engine import drop_db, create_db, session_maker
from database.orm_query import create_funnel, create_funnel_step

async def migrate_database():
    """Пересоздает базу данных с новой структурой для видео"""
    print("🔄 Пересоздаем базу данных...")
    
    try:
        # Удаляем старую базу
        await drop_db()
        print("✅ Старая база удалена")
        
        # Создаем новую базу
        await create_db()
        print("✅ Новая база создана")
    
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_database()) 