from services.imd_service import get_imd_data

result = get_imd_data("/api/v1/current_wx")

print(result)