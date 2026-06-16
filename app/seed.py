"""Seed de datos demo para Xpacio.

Crea 3 proveedores y ~30 espacios variados en Santiago (con coordenadas reales,
horarios, amenities, ratings y algunas ofertas activas) de forma idempotente.

Uso:
    python -m app.seed
"""
import asyncio
import uuid

import bcrypt
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.provider import Provider
from app.models.space import Space, SpaceSchedule, SpaceAmenity
from app.constants import UserRole, SpaceType, CancellationPolicy, DiscountType, VerificationStatus

# ── Proveedores demo ──────────────────────────────────────────────────────────

PROVIDERS = [
    dict(email="anfitrion@xpacio.cl",   password="xpacio1234", name="Anfitrión Demo",      bio="Espacios creativos en Santiago centro"),
    dict(email="espacios.sur@xpacio.cl", password="xpacio1234", name="Espacios Sur SpA",    bio="Recintos deportivos y eventos en el sur de Santiago"),
    dict(email="premium@xpacio.cl",      password="xpacio1234", name="Premium Venues",       bio="Venues de alto estándar para empresas"),
]

# ── Catálogo de espacios ──────────────────────────────────────────────────────
# provider_idx → índice en PROVIDERS (0, 1 o 2)

SPACES = [
    # ── OFICINAS ──────────────────────────────────────────────────────────────
    dict(provider_idx=0,
         name="Loft Creativo Lastarria", type=SpaceType.OFICINA,
         address="José Victorino Lastarria 70", city="Santiago",
         lat=-33.4372, lng=-70.6406, price=12000, capacity=8, rating=4.9, reviews=128,
         description="Loft luminoso en el corazón de Lastarria, ideal para reuniones y jornadas creativas. Techos de 4 metros y luz natural todo el día.",
         amenities=["Wifi 1 Gbps", "Café ilimitado", "Pizarra", "TV 4K", "Aire acondicionado"],
         discount=dict(type=DiscountType.PERCENTAGE, value=15, active=True, min_people=None),
         schedule=[(0,6,"08:00","21:00")]),

    dict(provider_idx=0,
         name="Coworking Ñuñoa Hub", type=SpaceType.OFICINA,
         address="Av. Irarrázaval 2700", city="Santiago",
         lat=-33.4560, lng=-70.5970, price=9000, capacity=6, rating=4.6, reviews=64,
         description="Espacio de coworking acogedor en Ñuñoa, ideal para equipos pequeños y reuniones de trabajo.",
         amenities=["Wifi", "Café", "Sala de reuniones", "Lockers"],
         discount=dict(type=DiscountType.PERCENTAGE, value=25, active=True, min_people=None),
         schedule=[(0,5,"07:30","20:00")]),

    dict(provider_idx=2,
         name="Suite Ejecutiva Las Condes", type=SpaceType.OFICINA,
         address="Av. Apoquindo 4501", city="Santiago",
         lat=-33.4128, lng=-70.5781, price=28000, capacity=12, rating=4.8, reviews=92,
         description="Suite de oficina premium en el sector financiero de Las Condes. Ideal para presentaciones y directorio.",
         amenities=["Videoconferencia 4K", "Recepcionista", "Café premium", "Impresora", "Estacionamiento"],
         discount=None,
         schedule=[(0,5,"08:00","20:00")]),

    dict(provider_idx=2,
         name="Oficina Modular Vitacura", type=SpaceType.OFICINA,
         address="Av. Nueva Costanera 3640", city="Santiago",
         lat=-33.3987, lng=-70.5873, price=22000, capacity=10, rating=4.7, reviews=47,
         description="Oficina modular con terraza privada y vistas al parque. Perfecta para equipos de tecnología.",
         amenities=["Terraza privada", "Wifi fibra óptica", "Cocina equipada", "Sala de descanso"],
         discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
         schedule=[(0,6,"07:00","22:00")]),

    dict(provider_idx=0,
         name="Espacio Colaborativo Matta", type=SpaceType.OFICINA,
         address="Av. Matta 1050", city="Santiago",
         lat=-33.4622, lng=-70.6441, price=8000, capacity=5, rating=4.4, reviews=33,
         description="Espacio colaborativo en barrio Italia. Ambiente relajado y creativo para freelancers y startups.",
         amenities=["Wifi", "Café y té", "Pizarra", "Planta"],
         discount=None,
         schedule=[(0,6,"09:00","21:00")]),

    dict(provider_idx=2,
         name="Boardroom Torre Titanium", type=SpaceType.OFICINA,
         address="Av. del Valle 555, Huechuraba", city="Santiago",
         lat=-33.3730, lng=-70.6260, price=35000, capacity=16, rating=4.9, reviews=211,
         description="Sala de directorio en el ícono de Huechuraba. Pantallas duales, sistema de audio profesional y catering.",
         amenities=["Pantallas duales", "Audio profesional", "Catering", "Recepción exclusiva", "Valet parking"],
         discount=None,
         schedule=[(0,5,"07:00","20:00")]),

    # ── CANCHAS ───────────────────────────────────────────────────────────────
    dict(provider_idx=1,
         name="Cancha Indoor Providencia", type=SpaceType.CANCHA,
         address="Av. Providencia 2100", city="Santiago",
         lat=-33.4258, lng=-70.6103, price=18000, capacity=20, rating=4.7, reviews=86,
         description="Cancha multiuso techada con piso flotante. Ideal para baby fútbol, vóleibol y básquetbol.",
         amenities=["Camarines", "Estacionamiento", "Iluminación LED", "Equipamiento incluido"],
         discount=dict(type=DiscountType.VOLUME, value=20, active=True, min_people=10),
         schedule=[(0,6,"07:00","23:00")]),

    dict(provider_idx=1,
         name="Complejo Deportivo La Florida", type=SpaceType.CANCHA,
         address="Av. Vicuña Mackenna 7110", city="Santiago",
         lat=-33.5120, lng=-70.5870, price=14000, capacity=24, rating=4.5, reviews=134,
         description="Canchas de pasto sintético certificado FIFA en La Florida. Iluminadas para juego nocturno.",
         amenities=["Pasto sintético FIFA", "Camarines con duchas", "Estacionamiento", "Cafetería"],
         discount=dict(type=DiscountType.VOLUME, value=15, active=True, min_people=12),
         schedule=[(0,6,"08:00","23:00")]),

    dict(provider_idx=1,
         name="Cancha Techada Maipú Arena", type=SpaceType.CANCHA,
         address="Av. Pajaritos 3501", city="Santiago",
         lat=-33.5120, lng=-70.7600, price=12000, capacity=18, rating=4.3, reviews=58,
         description="Cancha techada en Maipú con sistema de aire acondicionado. Ideal para ligas locales y torneos.",
         amenities=["Techo climatizado", "Camarines", "Estacionamiento gratuito", "Bar"],
         discount=None,
         schedule=[(0,6,"08:00","22:00")]),

    dict(provider_idx=1,
         name="Cancha de Tenis Club Santiago", type=SpaceType.CANCHA,
         address="Av. España 350", city="Santiago",
         lat=-33.4512, lng=-70.6601, price=10000, capacity=4, rating=4.8, reviews=72,
         description="Cancha de tenis en polvo de ladrillo con instructor disponible bajo solicitud.",
         amenities=["Polvo de ladrillo", "Raquetas disponibles", "Pelotas incluidas", "Duchas"],
         discount=dict(type=DiscountType.PERCENTAGE, value=20, active=True, min_people=None),
         schedule=[(0,6,"07:00","21:00")]),

    dict(provider_idx=1,
         name="Recinto Deportivo Pudahuel", type=SpaceType.CANCHA,
         address="Av. Americo Vespucio 1801", city="Santiago",
         lat=-33.4380, lng=-70.7750, price=9500, capacity=22, rating=4.1, reviews=29,
         description="Cancha multiuso al aire libre con tribuna pequeña. Perfecta para ligas escolares y eventos barriales.",
         amenities=["Tribuna", "Camarines básicos", "Iluminación", "Estacionamiento"],
         discount=None,
         schedule=[(0,6,"09:00","20:00")]),

    # ── SALAS ─────────────────────────────────────────────────────────────────
    dict(provider_idx=2,
         name="Sala Ejecutiva Skyline", type=SpaceType.SALA,
         address="Av. Andrés Bello 2425", city="Santiago",
         lat=-33.4179, lng=-70.6063, price=25000, capacity=14, rating=5.0, reviews=204,
         description="Sala de directorio con vista panorámica al cerro San Cristóbal, videoconferencia y catering opcional.",
         amenities=["Vista panorámica", "Videoconferencia", "Catering", "Recepcionista"],
         discount=None,
         schedule=[(0,5,"07:30","21:00")]),

    dict(provider_idx=0,
         name="Sala de Capacitación Agustinas", type=SpaceType.SALA,
         address="Agustinas 814", city="Santiago",
         lat=-33.4398, lng=-70.6516, price=15000, capacity=25, rating=4.6, reviews=88,
         description="Sala de capacitación en Santiago centro con proyector 4K, pantalla retráctil y sillas universitarias.",
         amenities=["Proyector 4K", "Pizarra inteligente", "Sillas universitarias", "Wifi", "Café"],
         discount=dict(type=DiscountType.PERCENTAGE, value=12, active=True, min_people=None),
         schedule=[(0,6,"08:00","22:00")]),

    dict(provider_idx=2,
         name="Sala Conferencias El Golf", type=SpaceType.SALA,
         address="Av. El Golf 99", city="Santiago",
         lat=-33.4175, lng=-70.5989, price=32000, capacity=20, rating=4.9, reviews=143,
         description="Sala de conferencias de alta gama en el sector financiero. Equipo de videoconferencia Cisco y traducción simultánea.",
         amenities=["Videoconferencia Cisco", "Traducción simultánea", "Catering premium", "Estacionamiento valet"],
         discount=None,
         schedule=[(0,5,"07:00","20:00")]),

    dict(provider_idx=0,
         name="Sala Multiuso Barrio Italia", type=SpaceType.SALA,
         address="Av. Italia 1020", city="Santiago",
         lat=-33.4530, lng=-70.6320, price=11000, capacity=18, rating=4.5, reviews=51,
         description="Sala versátil en Barrio Italia. Ideal para talleres, charlas y reuniones de equipo.",
         amenities=["Proyector", "Wifi", "Sillas y mesas movibles", "Cocina pequeña"],
         discount=dict(type=DiscountType.VOLUME, value=10, active=True, min_people=10),
         schedule=[(0,6,"09:00","21:00")]),

    dict(provider_idx=0,
         name="Sala de Reunión Estación Central", type=SpaceType.SALA,
         address="Av. Libertador O'Higgins 3363", city="Santiago",
         lat=-33.4556, lng=-70.6810, price=8500, capacity=10, rating=4.2, reviews=22,
         description="Sala de reuniones accesible en Estación Central. Cerca del metro y con estacionamiento.",
         amenities=["Proyector", "Wifi", "Pizarra", "Café"],
         discount=None,
         schedule=[(0,5,"08:00","20:00")]),

    # ── SALONES ───────────────────────────────────────────────────────────────
    dict(provider_idx=0,
         name="Salón de Eventos Bellavista", type=SpaceType.SALON,
         address="Pío Nono 250", city="Santiago",
         lat=-33.4330, lng=-70.6350, price=45000, capacity=120, rating=4.8, reviews=312,
         description="Galpón industrial recuperado con cielos altos. Perfecto para eventos corporativos, lanzamientos y cenas de gala.",
         amenities=["Sonido profesional", "Cocina equipada", "Barra", "DJ booth", "Iluminación escénica"],
         discount=None,
         schedule=[(4,6,"14:00","02:00")]),

    dict(provider_idx=2,
         name="Gran Salón Vitacura", type=SpaceType.SALON,
         address="Av. Vitacura 5250", city="Santiago",
         lat=-33.3950, lng=-70.5940, price=75000, capacity=200, rating=4.9, reviews=198,
         description="El salón más elegante de Vitacura. Jardines privados, salón principal y lobby de mármol. Ideal para matrimonios y eventos de empresa.",
         amenities=["Jardines privados", "Lobby de mármol", "Chef privado", "Valet parking", "Decoración"],
         discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
         schedule=[(4,6,"12:00","03:00")]),

    dict(provider_idx=1,
         name="Salón Club House Lo Barnechea", type=SpaceType.SALON,
         address="Av. La Dehesa 1700", city="Santiago",
         lat=-33.3790, lng=-70.5230, price=55000, capacity=150, rating=4.7, reviews=76,
         description="Club house con salón principal y quincho integrado. Vista a la cordillera y piscina disponible en temporada.",
         amenities=["Quincho", "Piscina (temporada)", "Vista cordillera", "Sonido", "Cocina industrial"],
         discount=None,
         schedule=[(4,6,"12:00","02:00")]),

    dict(provider_idx=1,
         name="Salón Industrial Yungay", type=SpaceType.SALON,
         address="Matucana 192", city="Santiago",
         lat=-33.4440, lng=-70.6680, price=38000, capacity=100, rating=4.6, reviews=55,
         description="Espacio industrial reconvertido en barrio Yungay. Ladrillo a la vista, vigas originales. Popular para matrimonios íntimos y exposiciones.",
         amenities=["Ladrillo a la vista", "Barra de bar", "Proyector", "Parking zona", "Cocina"],
         discount=dict(type=DiscountType.VOLUME, value=15, active=True, min_people=50),
         schedule=[(4,6,"13:00","02:00")]),

    # ── ESTUDIOS ──────────────────────────────────────────────────────────────
    dict(provider_idx=0,
         name="Estudio Fotográfico Norte", type=SpaceType.ESTUDIO,
         address="Av. Independencia 540", city="Santiago",
         lat=-33.4150, lng=-70.6530, price=22000, capacity=10, rating=4.9, reviews=156,
         description="Estudio con ciclorama infinito blanco e iluminación profesional Profoto. El favorito de los fotógrafos de moda en Santiago.",
         amenities=["Ciclorama blanco", "Luces Profoto", "Backstage", "Wifi", "Camarín"],
         discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
         schedule=[(0,6,"08:00","22:00")]),

    dict(provider_idx=0,
         name="Estudio de Grabación Santiago Sound", type=SpaceType.ESTUDIO,
         address="Av. Grecia 3070", city="Santiago",
         lat=-33.4640, lng=-70.5850, price=35000, capacity=8, rating=4.8, reviews=89,
         description="Estudio de grabación con sala de control Pro Tools, cabina insonorizada y sala de ensayo. Ideal para música, podcast y locuciones.",
         amenities=["Pro Tools", "Cabina insonorizada", "Micrófonos Neumann", "Monitores Genelec", "Sala de ensayo"],
         discount=None,
         schedule=[(0,6,"09:00","23:00")]),

    dict(provider_idx=2,
         name="Estudio Audiovisual Las Condes", type=SpaceType.ESTUDIO,
         address="Av. Apoquindo 6550", city="Santiago",
         lat=-33.4080, lng=-70.5640, price=45000, capacity=12, rating=4.7, reviews=62,
         description="Estudio de producción audiovisual con chroma key verde y azul, equipo de iluminación Arri y control room.",
         amenities=["Chroma key doble", "Iluminación Arri", "Control room", "Telepronter", "Aire acondicionado silencioso"],
         discount=dict(type=DiscountType.PERCENTAGE, value=15, active=True, min_people=None),
         schedule=[(0,5,"08:00","20:00")]),

    dict(provider_idx=1,
         name="Estudio de Arte y Cerámica Bellas", type=SpaceType.ESTUDIO,
         address="Av. Pedro de Valdivia 210", city="Santiago",
         lat=-33.4310, lng=-70.6148, price=15000, capacity=15, rating=4.5, reviews=41,
         description="Estudio de arte con horno de cerámica, mesas de trabajo y materiales disponibles. Para talleres, clases y proyectos artísticos.",
         amenities=["Horno de cerámica", "Mesas de trabajo", "Materiales básicos", "Wifi", "Lockers"],
         discount=None,
         schedule=[(0,6,"09:00","20:00")]),

    # ── TERRAZAS ──────────────────────────────────────────────────────────────
    dict(provider_idx=2,
         name="Terraza Sky Lounge Vitacura", type=SpaceType.TERRAZA,
         address="Av. Vitacura 4380", city="Santiago",
         lat=-33.3980, lng=-70.6010, price=38000, capacity=60, rating=4.9, reviews=98,
         description="Terraza outdoor con vista a la cordillera, fire pits y calefacción. El spot más instagrameable de Santiago.",
         amenities=["Vista cordillera", "Fire pits", "Calefactores", "Bar móvil", "Iluminación ambiental"],
         discount=None,
         schedule=[(3,6,"16:00","01:00")]),

    dict(provider_idx=0,
         name="Terraza Bellavista Rooftop", type=SpaceType.TERRAZA,
         address="Constitución 183", city="Santiago",
         lat=-33.4305, lng=-70.6370, price=28000, capacity=40, rating=4.7, reviews=74,
         description="Rooftop en Bellavista con vista al Cerro San Cristóbal. Ambientación bohemia y barra de cocktails.",
         amenities=["Vista Cerro San Cristóbal", "Barra de cocktails", "Calefactores", "Música ambiental"],
         discount=dict(type=DiscountType.PERCENTAGE, value=20, active=True, min_people=None),
         schedule=[(3,6,"17:00","01:00")]),

    dict(provider_idx=1,
         name="Terraza Maipú Garden", type=SpaceType.TERRAZA,
         address="Av. Américo Vespucio 1320", city="Santiago",
         lat=-33.5050, lng=-70.7650, price=18000, capacity=80, rating=4.3, reviews=38,
         description="Amplia terraza con jardín en Maipú. Ideal para eventos familiares, celebraciones y actividades outdoor.",
         amenities=["Jardín", "Parrilla", "Mesas y sillas", "Techo desplegable", "Estacionamiento"],
         discount=dict(type=DiscountType.VOLUME, value=12, active=True, min_people=30),
         schedule=[(4,6,"12:00","23:00")]),

    dict(provider_idx=2,
         name="Rooftop Torre Costanera", type=SpaceType.TERRAZA,
         address="Av. Andrés Bello 2447", city="Santiago",
         lat=-33.4168, lng=-70.6050, price=55000, capacity=50, rating=5.0, reviews=47,
         description="El rooftop más alto de Santiago en Torre Costanera. Vista de 360° de la ciudad. Exclusivo para grupos privados.",
         amenities=["Vista 360°", "Bar exclusivo", "Sommelier disponible", "Calefactores premium", "Seguridad privada"],
         discount=None,
         schedule=[(3,6,"18:00","02:00")]),
]


# ── Venues reales de Santiago con sub-espacios ────────────────────────────────
# Cada venue tiene sub_spaces: salas/áreas que se reservan individualmente.
VENUES_REALES = [
    dict(
        provider_idx=0,
        name="GAM - Centro Gabriela Mistral",
        type=SpaceType.SALON,
        address="Av. Libertador Bernardo O'Higgins 227",
        city="Santiago",
        lat=-33.4442, lng=-70.6535,
        price=80000, capacity=1000, rating=4.9, reviews=412,
        description="Ícono cultural de Santiago, el GAM ofrece salas de teatro, espacios de exposición y terrazas para eventos públicos y privados. Centro de artes y cultura en plena Alameda.",
        amenities=["Estacionamiento", "Restaurante", "Cafetería", "WiFi", "Acceso universal"],
        discount=None,
        schedule=[(0, 6, "09:00", "22:00")],
        sub_spaces=[
            dict(provider_idx=0, name="GAM - Sala A1", type=SpaceType.SALA,
                 address="Av. Libertador Bernardo O'Higgins 227", city="Santiago",
                 lat=-33.4442, lng=-70.6535, price=45000, capacity=220, rating=4.9, reviews=189,
                 description="Sala de teatro con graderías en U, ideal para obras, conferencias y presentaciones de hasta 220 personas. Equipo de iluminación y sonido profesional integrado.",
                 amenities=["Iluminación profesional", "Sonido profesional", "Cabina técnica", "Camarines", "Proyector"],
                 discount=None, schedule=[(0, 6, "09:00", "23:00")]),
            dict(provider_idx=0, name="GAM - Sala A2", type=SpaceType.SALA,
                 address="Av. Libertador Bernardo O'Higgins 227", city="Santiago",
                 lat=-33.4442, lng=-70.6535, price=35000, capacity=150, rating=4.8, reviews=142,
                 description="Sala multipropósito con piso de madera, ideal para talleres, ensayos de danza y eventos corporativos medianos.",
                 amenities=["Piso de madera", "Espejos", "Sonido", "Proyector", "Camarines"],
                 discount=None, schedule=[(0, 6, "09:00", "22:00")]),
            dict(provider_idx=0, name="GAM - Sala Isidora Zegers", type=SpaceType.SALA,
                 address="Av. Libertador Bernardo O'Higgins 227", city="Santiago",
                 lat=-33.4442, lng=-70.6535, price=28000, capacity=80, rating=4.7, reviews=98,
                 description="Sala íntima para conciertos de cámara, presentaciones literarias y seminarios. Acústica cuidada y ambiente recogido.",
                 amenities=["Acústica profesional", "Piano de cola", "Proyector", "Climatización"],
                 discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
                 schedule=[(0, 6, "10:00", "22:00")]),
            dict(provider_idx=0, name="GAM - Terraza", type=SpaceType.TERRAZA,
                 address="Av. Libertador Bernardo O'Higgins 227", city="Santiago",
                 lat=-33.4442, lng=-70.6535, price=55000, capacity=300, rating=4.9, reviews=67,
                 description="Terraza al aire libre en el techo del GAM con vistas a la Alameda y los cerros. Perfecta para lanzamientos, cocteles y eventos al atardecer.",
                 amenities=["Vista panorámica", "Bar móvil", "Iluminación ambiental", "Calefactores", "Acceso exclusivo"],
                 discount=None, schedule=[(3, 6, "16:00", "23:00")]),
        ],
    ),

    dict(
        provider_idx=2,
        name="Casona San Isidro - Barrio Italia",
        type=SpaceType.SALON,
        address="San Isidro 63",
        city="Santiago",
        lat=-33.4510, lng=-70.6480,
        price=60000, capacity=300, rating=4.8, reviews=234,
        description="Casona patrimonial de 1900 restaurada en el corazón de Barrio Italia. Patios interiores, salones con techos de 5 metros y jardín privado. El espacio favorito para matrimonios y eventos boutique en Santiago.",
        amenities=["Jardín privado", "Patios interiores", "Estacionamiento", "Cocina industrial", "WiFi"],
        discount=None,
        schedule=[(4, 6, "12:00", "02:00")],
        sub_spaces=[
            dict(provider_idx=2, name="Casona San Isidro - Salón Principal", type=SpaceType.SALON,
                 address="San Isidro 63", city="Santiago",
                 lat=-33.4510, lng=-70.6480, price=55000, capacity=180, rating=4.9, reviews=156,
                 description="Salón central de la casona con techos de 5 metros, vigas originales y ventanales hacia el jardín. Capacidad para banquetes y eventos formales.",
                 amenities=["Techos altos", "Vigas originales", "Sonido", "Iluminación decorativa", "Mesas y sillas"],
                 discount=None, schedule=[(4, 6, "12:00", "02:00")]),
            dict(provider_idx=2, name="Casona San Isidro - Patio Central", type=SpaceType.TERRAZA,
                 address="San Isidro 63", city="Santiago",
                 lat=-33.4510, lng=-70.6480, price=40000, capacity=120, rating=4.8, reviews=89,
                 description="Patio colonial empedrado con fuente central. Ideal para cócteles de recepción, ceremonias al aire libre y fotosesiones.",
                 amenities=["Fuente colonial", "Empedrado original", "Iluminación string lights", "Calefactores"],
                 discount=dict(type=DiscountType.PERCENTAGE, value=15, active=True, min_people=None),
                 schedule=[(4, 6, "12:00", "01:00")]),
            dict(provider_idx=2, name="Casona San Isidro - Sala de Reuniones", type=SpaceType.SALA,
                 address="San Isidro 63", city="Santiago",
                 lat=-33.4510, lng=-70.6480, price=18000, capacity=20, rating=4.7, reviews=44,
                 description="Sala histórica con chimenea y mobiliario de época, perfecta para reuniones ejecutivas íntimas o sesiones creativas.",
                 amenities=["Chimenea", "Mobiliario de época", "Proyector", "WiFi", "Servicio de café"],
                 discount=None, schedule=[(0, 5, "09:00", "20:00")]),
        ],
    ),

    dict(
        provider_idx=1,
        name="Centro de Artes Escénicas Matucana 100",
        type=SpaceType.SALON,
        address="Matucana 100",
        city="Santiago",
        lat=-33.4435, lng=-70.6680,
        price=70000, capacity=500, rating=4.7, reviews=318,
        description="Centro cultural en antigua maestranza ferroviaria. Espacio icónico del barrio Yungay con salas de teatro, galería y gran patio para festivales. Referente de la cultura independiente en Santiago.",
        amenities=["Patio de eventos", "Bar", "Galería de arte", "Camarines", "Estacionamiento"],
        discount=None,
        schedule=[(0, 6, "10:00", "23:00")],
        sub_spaces=[
            dict(provider_idx=1, name="Matucana 100 - Teatro Principal", type=SpaceType.SALA,
                 address="Matucana 100", city="Santiago",
                 lat=-33.4435, lng=-70.6680, price=65000, capacity=300, rating=4.8, reviews=201,
                 description="Teatro con estructura industrial original, graderías y escenario elevado. Referente para obras de teatro, conciertos alternativos y presentaciones performativas.",
                 amenities=["Escenario elevado", "Graderías", "Iluminación escénica", "Sonido profesional", "Camarines"],
                 discount=None, schedule=[(0, 6, "10:00", "23:00")]),
            dict(provider_idx=1, name="Matucana 100 - Galpón", type=SpaceType.SALON,
                 address="Matucana 100", city="Santiago",
                 lat=-33.4435, lng=-70.6680, price=50000, capacity=500, rating=4.7, reviews=134,
                 description="Enorme galpón de altura libre para festivales, ferias de arte, mercados y eventos masivos. Piso de hormigón y estructura industrial a la vista.",
                 amenities=["Altura libre 10m", "Carga eléctrica reforzada", "Acceso vehicular", "Baños industriales"],
                 discount=dict(type=DiscountType.VOLUME, value=20, active=True, min_people=100),
                 schedule=[(0, 6, "09:00", "23:00")]),
            dict(provider_idx=1, name="Matucana 100 - Sala Experimental", type=SpaceType.SALA,
                 address="Matucana 100", city="Santiago",
                 lat=-33.4435, lng=-70.6680, price=22000, capacity=60, rating=4.6, reviews=88,
                 description="Sala íntima para teatro experimental, performance art y presentaciones alternativas. Flexibilidad total en la disposición del espacio.",
                 amenities=["Piso flexible", "Riel de iluminación", "Sistema de sonido", "Gradas móviles"],
                 discount=None, schedule=[(0, 6, "10:00", "22:00")]),
        ],
    ),

    dict(
        provider_idx=2,
        name="Club de Golf Los Leones",
        type=SpaceType.SALON,
        address="Av. Presidente Riesco 3700",
        city="Santiago",
        lat=-33.4160, lng=-70.5900,
        price=90000, capacity=400, rating=4.9, reviews=187,
        description="Histórico club de golf en Las Condes con instalaciones de primer nivel. Salones clásicos, terraza con vista al campo de golf y servicio de catering exclusivo. El venue de preferencia para eventos corporativos de alto perfil.",
        amenities=["Vista al campo de golf", "Valet parking", "Catering exclusivo", "WiFi", "Sommelier"],
        discount=None,
        schedule=[(0, 6, "08:00", "23:00")],
        sub_spaces=[
            dict(provider_idx=2, name="Los Leones - Salón Cordillera", type=SpaceType.SALON,
                 address="Av. Presidente Riesco 3700", city="Santiago",
                 lat=-33.4160, lng=-70.5900, price=85000, capacity=300, rating=5.0, reviews=142,
                 description="El salón principal del club, con vista privilegiada a la cordillera nevada. Capacidad para 300 personas en formato banquete con servicio completo.",
                 amenities=["Vista cordillera", "Iluminación cristal", "Sonido integrado", "Catering", "Decoración floral"],
                 discount=None, schedule=[(0, 6, "08:00", "23:00")]),
            dict(provider_idx=2, name="Los Leones - Sala Directorio", type=SpaceType.SALA,
                 address="Av. Presidente Riesco 3700", city="Santiago",
                 lat=-33.4160, lng=-70.5900, price=40000, capacity=24, rating=4.9, reviews=98,
                 description="Sala de directorio presidencial para reuniones de alta dirección. Pantalla 8K, sistema de videoconferencia enterprise y servicio de butler.",
                 amenities=["Pantalla 8K", "Videoconferencia enterprise", "Butler", "Catering premium", "Estacionamiento VIP"],
                 discount=None, schedule=[(0, 5, "07:00", "20:00")]),
            dict(provider_idx=2, name="Los Leones - Terraza Jardines", type=SpaceType.TERRAZA,
                 address="Av. Presidente Riesco 3700", city="Santiago",
                 lat=-33.4160, lng=-70.5900, price=65000, capacity=200, rating=4.9, reviews=76,
                 description="Terraza con jardines perfectamente mantenidos y vista al campo de golf. Ideal para cócteles de lanzamiento, bodas al aire libre y eventos de primavera.",
                 amenities=["Jardines cuidados", "Vista golf", "Carpa disponible", "Bar premium", "Calefactores"],
                 discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
                 schedule=[(4, 6, "12:00", "23:00")]),
        ],
    ),

    dict(
        provider_idx=0,
        name="Fábrica de Arte - Barrio Yungay",
        type=SpaceType.ESTUDIO,
        address="Compañía de Jesús 1250",
        city="Santiago",
        lat=-33.4420, lng=-70.6650,
        price=25000, capacity=80, rating=4.6, reviews=155,
        description="Antigua fábrica industrial reconvertida en complejo de estudios creativos en el histórico barrio Yungay. Talleres de cerámica, estudio fotográfico y sala de ensayo musical bajo un mismo techo.",
        amenities=["Estacionamiento", "Cafetería", "WiFi fibra óptica", "Locker"],
        discount=None,
        schedule=[(0, 6, "08:00", "22:00")],
        sub_spaces=[
            dict(provider_idx=0, name="Fábrica de Arte - Estudio Fotográfico", type=SpaceType.ESTUDIO,
                 address="Compañía de Jesús 1250", city="Santiago",
                 lat=-33.4420, lng=-70.6650, price=22000, capacity=10, rating=4.7, reviews=87,
                 description="Estudio fotográfico con ciclorama negro y blanco, iluminación Profoto y set de accesorios. Ideal para moda, producto y fotografía artística.",
                 amenities=["Ciclorama negro/blanco", "Luces Profoto", "Camarín", "Set de accesorios", "Frigobar"],
                 discount=dict(type=DiscountType.PERCENTAGE, value=10, active=True, min_people=None),
                 schedule=[(0, 6, "08:00", "21:00")]),
            dict(provider_idx=0, name="Fábrica de Arte - Sala de Ensayo Musical", type=SpaceType.ESTUDIO,
                 address="Compañía de Jesús 1250", city="Santiago",
                 lat=-33.4420, lng=-70.6650, price=15000, capacity=8, rating=4.5, reviews=62,
                 description="Sala de ensayo insonorizada con batería, amplis de guitarra y bajo, micrófono y mezcladora básica. Todo incluido por hora.",
                 amenities=["Batería", "Amplificadores", "Insonorización", "Micrófono", "Mezcladora"],
                 discount=None, schedule=[(0, 6, "09:00", "23:00")]),
            dict(provider_idx=0, name="Fábrica de Arte - Taller de Cerámica", type=SpaceType.ESTUDIO,
                 address="Compañía de Jesús 1250", city="Santiago",
                 lat=-33.4420, lng=-70.6650, price=12000, capacity=12, rating=4.6, reviews=43,
                 description="Taller equipado con tornos, horno y materiales básicos para cerámica artesanal. Disponible para talleres privados, clases grupales y proyectos artísticos.",
                 amenities=["Tornos", "Horno cerámico", "Arcilla incluida", "Mesas de trabajo", "Mandiles"],
                 discount=None, schedule=[(0, 6, "09:00", "20:00")]),
        ],
    ),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        count = (await session.execute(select(func.count()).select_from(Space))).scalar_one()
        if count > 0:
            print(f"[seed] Ya existen {count} espacios — no se hace nada.")
            return

        providers_db: list[Provider] = []

        for pd in PROVIDERS:
            result = await session.execute(select(User).where(User.email == pd["email"]))
            user = result.scalar_one_or_none()
            if not user:
                pw = bcrypt.hashpw(pd["password"].encode(), bcrypt.gensalt(rounds=12)).decode()
                user = User(id=uuid.uuid4(), name=pd["name"], email=pd["email"],
                            password_hash=pw, role=UserRole.PROVIDER, phone="+56911111111")
                session.add(user)
                await session.flush()

            prov_res = await session.execute(select(Provider).where(Provider.user_id == user.id))
            provider = prov_res.scalar_one_or_none()
            if not provider:
                provider = Provider(id=uuid.uuid4(), user_id=user.id, bio=pd["bio"],
                                    verification_status=VerificationStatus.VERIFIED)
                session.add(provider)
                await session.flush()

            providers_db.append(provider)

        space_id_map: dict[str, uuid.UUID] = {}

        async def _create_space(sp: dict, parent_id: uuid.UUID | None = None) -> uuid.UUID:
            provider = providers_db[sp["provider_idx"]]
            sid = uuid.uuid4()
            space = Space(
                id=sid, provider_id=provider.id, name=sp["name"], type=sp["type"],
                description=sp["description"], address=sp["address"], city=sp["city"],
                lat=sp["lat"], lng=sp["lng"], price_per_hour=sp["price"], capacity=sp["capacity"],
                cancellation_policy=CancellationPolicy.FLEXIBLE, cancellation_hours=24,
                is_active=True, rating=sp["rating"], review_count=sp["reviews"],
                parent_id=parent_id,
            )
            d = sp.get("discount")
            if d:
                space.discount_type = d["type"]
                space.discount_value = d["value"]
                space.discount_active = d["active"]
                space.discount_min_people = d.get("min_people")
            session.add(space)
            await session.flush()

            for (d0, d1, op, cl) in sp["schedule"]:
                for dow in range(d0, d1 + 1):
                    session.add(SpaceSchedule(id=uuid.uuid4(), space_id=sid,
                                              day_of_week=dow, open_time=op, close_time=cl))

            for name in sp["amenities"]:
                session.add(SpaceAmenity(id=uuid.uuid4(), space_id=sid, name=name))

            return sid

        for sp in SPACES:
            await _create_space(sp)

        for venue in VENUES_REALES:
            parent_id = await _create_space(venue)
            space_id_map[venue["name"]] = parent_id
            for sub in venue.get("sub_spaces", []):
                await _create_space(sub, parent_id=parent_id)

        await session.commit()
        total = len(SPACES) + len(VENUES_REALES) + sum(len(v.get("sub_spaces", [])) for v in VENUES_REALES)
        print(f"[seed] Creados {total} espacios demo ({len(VENUES_REALES)} venues reales con sub-espacios).")
        print(f"Credenciales: anfitrion@xpacio.cl / xpacio1234")


async def seed_venues() -> None:
    """Agrega venues reales de Santiago con sub-espacios (idempotente por nombre)."""
    async with AsyncSessionLocal() as session:
        # Obtener un proveedor existente para asignar los venues
        prov_results = await session.execute(select(Provider).limit(3))
        providers_db = list(prov_results.scalars().all())
        if not providers_db:
            print("[seed_venues] No hay proveedores — corre seed() primero.")
            return

        # Asegurar 3 proveedores (reutilizar o repetir el primero)
        while len(providers_db) < 3:
            providers_db.append(providers_db[0])

        inserted = 0

        async def _create_venue_space(sp: dict, parent_id: uuid.UUID | None = None) -> uuid.UUID:
            existing = await session.execute(select(Space).where(Space.name == sp["name"]))
            existing_space = existing.scalar_one_or_none()
            if existing_space:
                return existing_space.id

            provider = providers_db[sp["provider_idx"]]
            sid = uuid.uuid4()
            space = Space(
                id=sid, provider_id=provider.id, name=sp["name"], type=sp["type"],
                description=sp["description"], address=sp["address"], city=sp["city"],
                lat=sp["lat"], lng=sp["lng"], price_per_hour=sp["price"], capacity=sp["capacity"],
                cancellation_policy=CancellationPolicy.FLEXIBLE, cancellation_hours=24,
                is_active=True, rating=sp["rating"], review_count=sp["reviews"],
                parent_id=parent_id,
            )
            d = sp.get("discount")
            if d:
                space.discount_type = d["type"]
                space.discount_value = d["value"]
                space.discount_active = d["active"]
                space.discount_min_people = d.get("min_people")
            session.add(space)
            await session.flush()

            for (d0, d1, op, cl) in sp["schedule"]:
                for dow in range(d0, d1 + 1):
                    session.add(SpaceSchedule(id=uuid.uuid4(), space_id=sid,
                                              day_of_week=dow, open_time=op, close_time=cl))
            for name in sp["amenities"]:
                session.add(SpaceAmenity(id=uuid.uuid4(), space_id=sid, name=name))

            nonlocal inserted
            inserted += 1
            return sid

        for venue in VENUES_REALES:
            parent_id = await _create_venue_space(venue)
            for sub in venue.get("sub_spaces", []):
                await _create_venue_space(sub, parent_id=parent_id)

        await session.commit()
        print(f"[seed_venues] {inserted} nuevos espacios insertados.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "venues":
        asyncio.run(seed_venues())
    else:
        asyncio.run(seed())
