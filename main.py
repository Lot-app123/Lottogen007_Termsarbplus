import io
import random
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated
from urllib.parse import quote
from typing import Annotated, Optional


from fastapi import Cookie, Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from PIL import Image, ImageDraw, ImageFont
from zoneinfo import ZoneInfo

# ─── App setup ───────────────────────────────────────────────────────────────

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─── Auth config (เปลี่ยน SECRET_KEY ก่อน deploy!) ───────────────────────────

SECRET_KEY = "change-me-before-deploy-use-openssl-rand-hex-32"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 8

USERS = {"admin": "1234"}  # TODO: ใช้ DB + bcrypt จริง ๆ ใน production

# Mapping สำหรับรูปธง (อัปเดตตามชื่อที่มีการรวมรอบ + VIP และ เช้า/บ่าย)
FLAG_MAPPING = {
    # 🇱🇦 ลาว (Laos)
    "ลาว EXTRA": "static/flags/laos.png",
    "หวยลาว EXTRA": "static/flags/laos.png",
    "ลาว TV": "static/flags/laos.png",
    "หวยลาว TV": "static/flags/laos.png",
    "ลาวพิเศษรอบเที่ยง": "static/flags/laos.png",
    "ลาว HD": "static/flags/laos.png",
    "หวยลาว HD": "static/flags/laos.png",
    "ลาวสตาร์": "static/flags/laos.png",
    "หวยลาวสตาร์": "static/flags/laos.png",
    "หวยลาวสามัคคี": "static/flags/laos.png",# ปรับตามชื่อใหม่
    "ลาวสามัคคี": "static/flags/laos.png",
    "ลาวพัฒนา": "static/flags/laos.png",
    "ลาวอาเซียน": "static/flags/laos.png",
    "ลาว VIP": "static/flags/laos.png",
    "หวยลาว VIP": "static/flags/laos.png",
    "ลาวสามัคคี VIP": "static/flags/laos.png",
    "หวยลาวสามัคคี VIP": "static/flags/laos.png",
    "ลาว STAR VIP": "static/flags/laos.png",
    "หวยลาว STAR VIP": "static/flags/laos.png",
    "ลาวกาชาด": "static/flags/laos.png",
    "หวยลาวกาชาด": "static/flags/laos.png",


    # 🇻🇳 เวียดนาม (Vietnam)
    "ฮานอยอาเซียน": "static/flags/vietnam.png",
    "ฮานอย HD": "static/flags/vietnam.png",
    "ฮานอยสตาร์": "static/flags/vietnam.png",
    "ฮานอย TV": "static/flags/vietnam.png",
    "หวยฮานอย TV": "static/flags/vietnam.png",
    "ฮานอยกาชาด": "static/flags/vietnam.png",
    "หวยฮานอยกาชาด": "static/flags/vietnam.png",
    "ฮานอยพิเศษ": "static/flags/vietnam.png",
    "ฮานอยสามัคคี": "static/flags/vietnam.png",
    "ฮานอย": "static/flags/vietnam.png", # ปรับตามชื่อใหม่
    "ฮานอยปกติ": "static/flags/vietnam.png",
    "ฮานอยดึก": "static/flags/vietnam.png",
    "หวยฮานอย": "static/flags/vietnam.png",
    "ฮานอย VIP": "static/flags/vietnam.png",
    "หวยฮานอย VIP": "static/flags/vietnam.png",
    "ฮานอยพัฒนา": "static/flags/vietnam.png",
    "ฮานอย EXTRA": "static/flags/vietnam.png",
    "หวยฮานอย EXTRA": "static/flags/vietnam.png",

    # 🇯🇵 ญี่ปุ่น (Japan)
    "นิเคอิ(เช้า)": "static/flags/japan.png",
    "นิเคอิเช้า": "static/flags/japan.png",
    "นิเคอิ(เช้า) VIP": "static/flags/japan.png",
    "นิเคอิเช้า VIP": "static/flags/japan.png",
    "นิเคอิ(บ่าย)": "static/flags/japan.png",
    "นิเคอิบ่าย": "static/flags/japan.png",
    "นิเคอิ(บ่าย) VIP": "static/flags/japan.png",
    "นิเคอิบ่าย VIP": "static/flags/japan.png",

    # 🇨🇳 จีน (China)
    "จีน(เช้า)": "static/flags/china.png",
    "จีนเช้า": "static/flags/china.png",
    "จีน(เช้า) VIP": "static/flags/china.png",
    "จีนเช้า VIP": "static/flags/china.png",
    "จีน(บ่าย)": "static/flags/china.png",
    "จีนบ่าย": "static/flags/china.png",
    "จีน(บ่าย) VIP": "static/flags/china.png",
    "จีนบ่าย VIP": "static/flags/china.png",

    # 🇭🇰 ฮ่องกง (Hong Kong)
    "ฮั่งเส็ง(เช้า)": "static/flags/hongkong.png",
    "ฮั่งเส็งเช้า": "static/flags/hongkong.png",
    "ฮั่งเส็ง(เช้า) VIP": "static/flags/hongkong.png",
    "ฮั่งเส็งเช้า VIP": "static/flags/hongkong.png",
    "ฮั่งเส็ง(บ่าย)": "static/flags/hongkong.png",
    "ฮั่งเส็งบ่าย": "static/flags/hongkong.png",
    "ฮั่งเส็ง(บ่าย) VIP": "static/flags/hongkong.png",
    "ฮั่งเส็งบ่าย VIP": "static/flags/hongkong.png",

    # 🇹🇼 ไต้หวัน (Taiwan)
    "ไต้หวัน": "static/flags/taiwan.png",
    "ไต้หวัน VIP": "static/flags/taiwan.png",

    # 🇰🇷 เกาหลีใต้ (South Korea)
    "เกาหลี": "static/flags/korea.png",
    "เกาหลี VIP": "static/flags/korea.png",

    # 🇺🇸 สหรัฐอเมริกา (USA)
    "ดาวโจนส์": "static/flags/usa.png",
    "ดาวโจนส์ VIP": "static/flags/usa.png",
    "หวยดาวโจนส์ VIP": "static/flags/usa.png",
    "ดาวโจนส์ STAR": "static/flags/usa.png",
    "หวยดาวโจนส์ STAR": "static/flags/usa.png",

    # 🇬🇧 อังกฤษ (United Kingdom)
    "อังกฤษ": "static/flags/uk.png",
    "อังกฤษ VIP": "static/flags/uk.png",

    # 🇩🇪 เยอรมนี (Germany)
    "เยอรมัน": "static/flags/germany.png",
    "เยอรมัน VIP": "static/flags/germany.png",

    # 🇷🇺 รัสเซีย (Russia)
    "รัสเซีย": "static/flags/russia.png",
    "รัสเซีย VIP": "static/flags/russia.png",

    # 🇸🇬 สิงคโปร์ (Singapore)
    "สิงคโปร์": "static/flags/singapore.png",
    "สิงคโปร์ VIP": "static/flags/singapore.png",

    # 🇹🇭 ไทย (Thailand)
    "ไทยเช้า": "static/flags/thailand.png",
    "ไทยเที่ยง": "static/flags/thailand.png",
    "ไทยบ่าย": "static/flags/thailand.png",
    "ไทยเย็น": "static/flags/thailand.png",
    "ไทย": "static/flags/thailand.png",
    "ออมสิน": "static/flags/thailand.png",
    "ธกส": "static/flags/thailand.png",
    "รัฐบาลไทย": "static/flags/thailand.png",

    # 🇮🇳 อินเดีย (India)
    "อินเดีย": "static/flags/india.png",

    # 🇲🇾 มาเลเซีย (Malaysia)
    "มาเลย์": "static/flags/malaysia.png",
    "หวยมาเลย์": "static/flags/malaysia.png",

    # 🇪🇬 อียิปต์ (Egypt)
    "อียิปต์": "static/flags/egypt.png",

    # 🇪🇺 ยุโรป (Europe)
    "ยูโร": "static/flags/eu.png"
}


def create_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Cookie(default=None, alias="access_token")) -> str:
    if not token:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": "/login"})


CurrentUser = Annotated[str, Depends(get_current_user)]


# ─── Image/font cache (โหลดครั้งเดียวตอน startup) ───────────────────────────

@lru_cache(maxsize=1)
def _load_bg() -> Image.Image:
    """โหลดภาพพื้นหลังครั้งเดียว แล้ว cache ไว้ใน RAM"""
    return Image.open("static/LottoGen Template1.jpg").convert("RGBA")


@lru_cache(maxsize=16) # เพิ่มขนาด cache เผื่อโหลดหลายฟอนต์
def _load_font(size: int, font_path: str = "static/Kanit-SemiBold.ttf") -> ImageFont.FreeTypeFont:
    """Cache แต่ละขนาดและไฟล์ฟอนต์แยกกัน (ค่าเริ่มต้นคือ COOOPBL สำหรับตัวเลข)"""
    return ImageFont.truetype(font_path, size)


def _get_auto_font(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                   start: int = 50, min_size: int = 20, 
                   font_path: str = "static/Kanit-SemiBold.ttf") -> ImageFont.FreeTypeFont:
    for size in range(start, min_size - 1, -1):
        font = _load_font(size, font_path)
        w = draw.textbbox((0, 0), text, font=font)[2]
        if w <= max_width:
            return font
    return _load_font(min_size, font_path)


def _bold_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
               font: ImageFont.FreeTypeFont, fill: str = "#ffca08", boldness: int = 1) -> None:
    x, y = xy
    for dx in range(-boldness, boldness + 1):
        for dy in range(-boldness, boldness + 1):
            draw.text((x + dx, y + dy), text, font=font, fill=fill)


def create_image_bytes(
    lottery_type: str, 
    main1: Optional[str] = None, 
    main2: Optional[str] = None,
    pair1: Optional[str] = None,
    pair2: Optional[str] = None,
    pair3: Optional[str] = None,
    triple1: Optional[str] = None,
    triple2: Optional[str] = None,
    win_num: Optional[str] = None
) -> bytes:
    image = deepcopy(_load_bg()).convert("RGB")
    draw  = ImageDraw.Draw(image)

    # ─── วันที่และหัวข้อ ──────────────────────────────────────────────────
    # ปรับ format วันที่เป็น วัน/เดือน (DD/MM) ตามแบบในภาพ image_7a769f.png
    text_font_path = "static/Kanit-SemiBold.ttf"
    date_text = datetime.now(ZoneInfo("Asia/Bangkok")).strftime("%d/%m/%y")
    draw.text((450, 150 ), date_text, font=_load_font(50 ,font_path=text_font_path), fill="#ffffff",stroke_width=2, stroke_fill="#000000") # อาจต้องปรับพิกัด x,y ตามพื้นหลังจริง

    text_font_path = "static/Kanit-SemiBold.ttf"
    font_auto = _get_auto_font(draw, lottery_type, image.width - 400, start=70, font_path=text_font_path)
    bbox = draw.textbbox((0, 0), lottery_type, font=font_auto)
    text_width = bbox[2] - bbox[0]
    x_pos = (image.width - text_width) // 2
    text_start_x = x_pos + 30
    draw.text((text_start_x, 70), lottery_type, font=font_auto, fill="#f4c66b",stroke_width=3, stroke_fill="#000000")

    flag_path = FLAG_MAPPING.get(lottery_type)
    if flag_path:
        try:
            # โหลดรูปธง
            flag_img = Image.open(flag_path).convert("RGBA")
            
            # 1. กำหนดขนาดธง
            target_flag_width = 100   # ⬅️ ปรับขนาดความกว้างของธงที่นี่
            w_ratio = target_flag_width / flag_img.width
            target_flag_height = int(flag_img.height * w_ratio)
            flag_img = flag_img.resize((target_flag_width, target_flag_height), Image.Resampling.LANCZOS)
            
            # 2. กำหนดตำแหน่งที่วางธงให้ต่อท้ายชื่อหวย
            spacing = 20 # ⬅️ ปรับระยะห่างระหว่างตัวอักษรกับธงได้ที่นี่
            
            # คำนวณแกน X: เอาจุดเริ่มต้นข้อความ + ความกว้างข้อความ + ระยะห่าง
            flag_x = text_start_x + text_width + spacing 
            flag_y = 95  # ⬅️ แกน Y ยึดตามเดิม (ปรับขึ้นลงให้ตรงกับข้อความได้)
            
            # วางรูปธงทับลงไป
            image.paste(flag_img, (int(flag_x), int(flag_y)), flag_img)
            
        except FileNotFoundError:
            pass # ถ้าหาไฟล์รูปธงไม่เจอ ให้ข้ามการวาดธงไปเลย

    # 1. จัดการ Main 1 (วิ่ง/รูด 1 ตัว) และ Main 2 (เน้นพิเศษ 2 ตัว)
    m1 = main1 if main1 and len(main1) == 1 and main1.isdigit() else None
    m2 = main2 if main2 and len(main2) == 2 and main2.isdigit() else None

    if m1 and m2:
        num1, num2 = m1, m2
    elif m1:
        num1 = m1
        avail = [str(i) for i in range(10) if str(i) != num1]
        num2 = num1 + random.choice(avail)
        if random.random() > 0.5: num2 = num2[::-1]
    elif m2:
        num2 = m2
        num1 = random.choice(list(num2))
    else:
        n1, n2 = random.sample(range(10), 2)
        num1 = str(n1)
        num2 = str(n1) + str(n2)
        if random.random() > 0.5: num2 = num2[::-1]

    # 2. จัดการ เลขคู่ 3 ชุด
    def get_or_random_pair(user_input, default_format):
        if user_input and len(user_input) == 2 and user_input.isdigit():
            return user_input
        return default_format

    avail_digits = [str(i) for i in range(10) if str(i) not in num2]
    r1, r2, r3 = random.sample(avail_digits, 3) if len(avail_digits) >= 3 else (random.choice(avail_digits), random.choice(avail_digits), random.choice(avail_digits))
    
    pairs_list = [
        get_or_random_pair(pair1, f"{num1}{r1}"),
        get_or_random_pair(pair2, f"{num1}{r2}"),
        get_or_random_pair(pair3, f"{num1}{r3}")
    ]

    # 3. จัดการ เลข 3 ตัว 2 ชุด
    def get_or_random_triple(user_input, default_format):
        if user_input and len(user_input) == 3 and user_input.isdigit():
            return user_input
        return default_format

    tr1, tr2, tr3, tr4 = random.sample(avail_digits, 4) if len(avail_digits) >= 4 else (random.choice(avail_digits), random.choice(avail_digits), random.choice(avail_digits), random.choice(avail_digits))
    
    triple_list = [
        get_or_random_triple(triple1, f"{num1}{tr1}{tr2}"),
        get_or_random_triple(triple2, f"{num1}{tr3}{tr4}")
    ]

    # 4. จัดการ เลขวิน 6 ตัว
    if win_num and len(win_num) == 6 and win_num.isdigit():
        random_6 = win_num
    else:
        needed = list(set(num2))
        others = [str(i) for i in range(10) if str(i) not in needed]
        fillers = random.sample(others, 6 - len(needed))
        six = needed + fillers
        random.shuffle(six)
        random_6 = "".join(six)

    # ─── วาดผลลัพธ์ลงบนภาพ ────────────────────────────────────────────────
    f_Superlarge  = _load_font(170)
    f_large  = _load_font(130)
    f_medium = _load_font(90)
    f_small  = _load_font(80)
    f_Supersmall  = _load_font(70)

    draw.text((415, 360), f"{num1}", font = f_Superlarge, fill="#ffffff",stroke_width=3, stroke_fill="#000000" )
    draw.text((720, 395), f"{num2}", font = f_large, fill="#920000",stroke_width=2, stroke_fill="#000000")
    
    for i, pair in enumerate(pairs_list):
        draw.text((210 + i * 150, 700), pair, font = f_medium, fill="#f4c66b",stroke_width=2, stroke_fill="#000000")
        
    draw.text((720, 665), triple_list[0], font=f_small, fill="#920000",stroke_width=2, stroke_fill="#000000")
    draw.text((720, 755), triple_list[1], font=f_small, fill="#920000",stroke_width=2, stroke_fill="#000000")

    spaced_random_6 = "   ".join(random_6)
    draw.text((397, 875), spaced_random_6, font = f_small, fill="#ffffff",stroke_width=2, stroke_fill="#000000") 

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=85, optimize=True)
    buf.seek(0)
    return buf.read()

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    if USERS.get(username) != password:
        raise HTTPException(status_code=400, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="access_token",
        value=create_token(username),
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
    )
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

# ─── โค้ดส่วนนี้คือตัวที่หายไป และทำให้เกิด Error 405 Method Not Allowed ───
@app.get("/", response_class=HTMLResponse)
async def lottery_page(request: Request, user: CurrentUser):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})
# ───────────────────────────────────────────────────────────────────────

@app.post("/")
async def lottery_generate(
    user: CurrentUser,
    lottery_type: list[str] = Form(...),
    main1: Optional[str] = Form(None), 
    main2: Optional[str] = Form(None),
    pair1: Optional[str] = Form(None), 
    pair2: Optional[str] = Form(None), 
    pair3: Optional[str] = Form(None), 
    triple1: Optional[str] = Form(None),
    triple2: Optional[str] = Form(None),
    win_num: Optional[str] = Form(None), 
):
    # ... โค้ดเดิมของคุณที่ใช้รับค่าและสร้างรูปภาพ ...
    if not lottery_type:
        raise HTTPException(status_code=400, detail="กรุณาเลือกประเภทหวยอย่างน้อย 1 รายการ")

    # --- เริ่มต้นส่วนตรวจสอบเงื่อนไขตัวเลข (Backend Validation) ---
    if main2 and len(main2) == 2:
        if not main1:
            raise HTTPException(status_code=400, detail="กรุณาระบุ วิ่ง/รูด ก่อน")
        if main1 not in main2:
            raise HTTPException(status_code=400, detail=f"เน้นพิเศษ ({main2}) ต้องมีเลขจาก วิ่ง/รูด ({main1})")

    seen_pairs = set()
    for i, p in enumerate([pair1, pair2, pair3], 1):
        if p and len(p) == 2:
            if not main1 or main1 not in p:
                raise HTTPException(status_code=400, detail=f"เลขคู่ชุดที่ {i} ต้องมีเลขจาก วิ่ง/รูด")
            # --- กฎใหม่: ห้ามซ้ำกับเน้นพิเศษ ---
            if main2 and p == main2:
                raise HTTPException(status_code=400, detail=f"เลขคู่ชุดที่ {i} ห้ามซ้ำกับเน้นพิเศษ ({main2})")
            # --- กฎใหม่: ห้ามซ้ำกันเอง ---
            if p in seen_pairs:
                raise HTTPException(status_code=400, detail=f"เลขคู่ซ้ำกัน กรุณาเปลี่ยนเลขใหม่")
            seen_pairs.add(p)

    seen_triples = set()
    for i, t in enumerate([triple1, triple2], 1):
        if t and len(t) == 3:
            if not main1 or main1 not in t:
                raise HTTPException(status_code=400, detail=f"เลข 3 ตัวชุดที่ {i} ต้องมีเลขจาก วิ่ง/รูด")
            # --- กฎใหม่: ห้ามซ้ำกันเอง ---
            if t in seen_triples:
                raise HTTPException(status_code=400, detail=f"เลข 3 ตัวซ้ำกัน กรุณาเปลี่ยนเลขใหม่")
            seen_triples.add(t)
            
    if win_num and len(win_num) == 6:
        if not main2 or len(main2) < 2:
            raise HTTPException(status_code=400, detail="กรุณาระบุ เน้นพิเศษ ก่อนพิมพ์เลขวิน")
        for d in main2:
            if d not in win_num:
                raise HTTPException(status_code=400, detail=f"เลขวินต้องมีตัวเลขจาก เน้นพิเศษ ({main2})")
    # --- สิ้นสุดส่วนตรวจสอบเงื่อนไขตัวเลข ---

    parsed_items = []
    for lt_data in lottery_type:
        time_str, name_str = lt_data.split("|", 1) if "|" in lt_data else ("", lt_data)
        parsed_items.append({
            "time": time_str, 
            "name": name_str
        })
    
    parsed_items.sort(key=lambda x: x["time"] if x["time"] else "99:99")

    if len(parsed_items) == 1:
        item = parsed_items[0]
        time_str = item["time"]
        name_str = item["name"]
        
        filename = f"{time_str.replace(':', '.')}_{name_str}.jpg" if time_str else f"{name_str}.jpg"
        encoded_filename = quote(filename)
        
        img_bytes = create_image_bytes(name_str, main1, main2, pair1, pair2, pair3, triple1, triple2, win_num)
        return StreamingResponse(
            io.BytesIO(img_bytes),
            media_type="image/jpeg",
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"},
        )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, item in enumerate(parsed_items, start=1):
            time_str = item["time"]
            name_str = item["name"]
            
            prefix = f"{index:02d}_" 
            time_part = f"{time_str.replace(':', '.')}_" if time_str else ""
            filename = f"{prefix}{time_part}{name_str}.jpg"
            
            zf.writestr(filename, create_image_bytes(name_str, main1, main2, pair1, pair2, pair3, triple1, triple2, win_num))
    zip_buf.seek(0)

    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="lottery_results.zip"'},
    )

# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=False)
