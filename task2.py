import math

# Вхідні дані
LATITUDE = 50.603694
LONGITUDE = 30.650625
AZIMUTH = 335
PIXEL_SIZE_METERS = 0.38

center_x = 320
center_y = 256

point_x_center = 558
point_y_center = 328

# знайдемо зміщення в пікселях (з урахуванням напрямку осей)
delta_x_pixels = center_x - point_x_center
delta_y_pixels = point_y_center - center_y

# переведемо зміщення в метри
dx_meters = delta_x_pixels * PIXEL_SIZE_METERS
dy_meters = delta_y_pixels * PIXEL_SIZE_METERS

# азимут напрямку вгору на зображенні
azimuth_rad = math.radians(AZIMUTH)

# обертаємо вектор
north_offset = dy_meters * math.cos(azimuth_rad) - dx_meters * math.sin(azimuth_rad)
east_offset = dy_meters * math.sin(azimuth_rad) + dx_meters * math.cos(azimuth_rad)

# метрів у градусі
meters_per_degree_lat = 110600
meters_per_degree_lon = 110600 * math.cos(math.radians(LATITUDE))

delta_lat = north_offset / meters_per_degree_lat
delta_lon = east_offset / meters_per_degree_lon

# координати центру
center_lat = LATITUDE + delta_lat
center_lon = LONGITUDE + delta_lon

maps_url = f"https://www.google.com/maps?q={center_lat},{center_lon}"
print(f"Координати центру зображення:\nШирота: {center_lat:.6f}\nДовгота: {center_lon:.6f}")
print(maps_url)
