import io
import random
import zipfile
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Annotated, Optional
from urllib.parse import quote

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

# ─── Auth config ─────────────────────────────────────────────────────────────

SECRET_KEY = "change-me-before-deploy-use-openssl-rand-hex-32"
ALGORITHM  = "HS256"
TOKEN_EXPIRE_HOURS = 8

USERS = {"ts11111": "1234"}

# Mapping สำหรับรูปธง
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
    "หวยลาวสามัคคี": "static/flags/laos.png",
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
    "ฮานอย": "static/flags/vietnam.png",
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

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]

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

# ─── Image/font cache ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_bg() -> Image.Image:
    """โหลดภาพพื้นหลัง T1.jpg ครั้งเดียว"""
    return Image.open("static/T1.jpg").convert("RGBA")

@lru_cache(maxsize=16)
def _load_font(size: int, font_path: str = "static/Kanit-Light.ttf") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(font_path, size)

def _get_auto_font(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                   start: int = 70, min_size: int = 30, 
                   font_path: str = "static/Kanit-Light.ttf") -> ImageFont.FreeTypeFont:
    for size in range(start, min_size - 1, -1):
        font = _load_font(size, font_path)
        w = draw.textbbox((0, 0), text, font=font)[2]
        if w <= max_width:
            return font
    return _load_font(min_size, font_path)

def draw_text_center(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.FreeTypeFont,
                     fill: str = "#ffffff", stroke_w: int = 2, stroke_fill: str = "#000000") -> None:
    x_center, y_center = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = x_center - (w // 2)
    y = y_center - (h // 2)
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_w, stroke_fill=stroke_fill)

# ─── ฟังก์ชันวาดภาพตามรูปแบบ T2 บนแม่แบบ T1 ──────────────────────────────────

def create_image_bytes(
    lottery_type: str, 
    main1: Optional[str] = None, 
    main2: Optional[str] = None,
    bracket: Optional[str] = None,
    den_rong: Optional[str] = None,
    pair1: Optional[str] = None, pair2: Optional[str] = None, pair3: Optional[str] = None,
    pair4: Optional[str] = None, pair5: Optional[str] = None, pair6: Optional[str] = None,
    triple1: Optional[str] = None, triple2: Optional[str] = None, triple3: Optional[str] = None,
    double1: Optional[str] = None, double2: Optional[str] = None, win_num: Optional[str] = None
) -> bytes:
    image = deepcopy(_load_bg()).convert("RGB")
    draw  = ImageDraw.Draw(image)
    text_font_path = "static/Kanit-Light.ttf"

    # 1. วาดชื่อหวย + ธง และ วันที่ (เหมือนเดิม)
    font_title = _get_auto_font(draw, lottery_type, 650, start=110, font_path=text_font_path)
    title_center_x, title_center_y = 760, 150
    draw_text_center(draw, (title_center_x, title_center_y), lottery_type, font_title, fill="#ffffff", stroke_w=5, stroke_fill="#0D2207")

    bbox_title = draw.textbbox((0, 0), lottery_type, font=font_title)
    text_w = bbox_title[2] - bbox_title[0]
    title_start_x = title_center_x - (text_w // 2)

    flag_path = FLAG_MAPPING.get(lottery_type)
    if flag_path:
        try:
            flag_img = Image.open(flag_path).convert("RGBA")
            target_flag_w = 80
            w_ratio = target_flag_w / flag_img.width
            target_flag_h = int(flag_img.height * w_ratio)
            flag_img = flag_img.resize((target_flag_w, target_flag_h), Image.Resampling.LANCZOS)
            spacing = 15
            flag_y = int(title_center_y - (target_flag_h // 50))
            image.paste(flag_img, (int(title_start_x - target_flag_w - spacing), flag_y), flag_img)
            image.paste(flag_img, (int(title_start_x + text_w + spacing), flag_y), flag_img)
        except FileNotFoundError:
            pass

    now = datetime.now(ZoneInfo("Asia/Bangkok"))
    date_text = f"วันที่ {now.day} {THAI_MONTHS[now.month]} {now.year + 543}"
    draw_text_center(draw, (760, 280), date_text, _load_font(44, font_path=text_font_path), fill="#ffffff", stroke_w=1, stroke_fill="#000000")

    # 3. จัดการตัวเลข วิ่ง(num1) - รูด(num2) ให้ไม่ซ้ำกัน
    m1 = main1 if main1 and len(main1) == 1 and main1.isdigit() else None
    m2 = main2 if main2 and len(main2) == 1 and main2.isdigit() else None

    if m1 and m2:
        num1, num2 = m1, m2
    elif m1:
        num1 = m1
        num2 = random.choice([str(i) for i in range(10) if str(i) != num1])
    elif m2:
        num2 = m2
        num1 = random.choice([str(i) for i in range(10) if str(i) != num2])
    else:
        num1, num2 = random.sample([str(i) for i in range(10)], 2)

    # 4. วาดช่อง วิ่ง - รูด และ วงเล็บ (บังคับวงเล็บเป็นวิ่งรูดตามลำดับ)
    br_val = bracket if bracket and len(bracket) == 2 else f"{num1}{num2}"
    f_run = _load_font(120, font_path=text_font_path)
    draw_text_center(draw, (635, 430), f"{num1} - {num2}", f_run, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (922, 450), f"({br_val})", _load_font(72, font_path=text_font_path), fill="#ffffff", stroke_w=2, stroke_fill="#000000")

    # 5. เด่นรอง
    val_den_rong = den_rong if den_rong and len(den_rong) == 2 else f"1{random.choice([str(i) for i in range(10) if str(i) not in (num1, num2)])}"
    f_side = _load_font(90, font_path=text_font_path)
    draw_text_center(draw, (160, 665), val_den_rong, f_side, fill="#ffffff", stroke_w=2, stroke_fill="#000000")

    # 6. กันเบิ้ล (บังคับเบิ้ลวิ่ง และ เบิ้ลรูด)
    db1 = double1 if double1 and len(double1) == 2 else f"{num1}{num1}"
    db2 = double2 if double2 and len(double2) == 2 else f"{num2}{num2}"
    draw_text_center(draw, (1120, 665), db1, f_side, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (1120, 775), db2, f_side, fill="#ffffff", stroke_w=2, stroke_fill="#000000")

    # 7. เลขคู่ 6 ชุด (แถวบนขึ้นด้วยวิ่ง แถวล่างขึ้นด้วยรูด)
    def get_pair(user_val, default_val): return user_val if user_val and len(user_val) == 2 else default_val
    
    r1, r2, r3 = random.sample([str(i) for i in range(10) if str(i) != num1], 3)
    p1 = get_pair(pair1, f"{num1}{r1}"); p2 = get_pair(pair2, f"{num1}{r2}"); p3 = get_pair(pair3, f"{num1}{r3}")
    
    r4, r5, r6 = random.sample([str(i) for i in range(10) if str(i) != num2], 3)
    p4 = get_pair(pair4, f"{num2}{r4}"); p5 = get_pair(pair5, f"{num2}{r5}"); p6 = get_pair(pair6, f"{num2}{r6}")

    f_pairs = _load_font(95, font_path=text_font_path)
    draw_text_center(draw, (490, 605), p1, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (655, 605), p2, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (820, 605), p3, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (490, 735), p4, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (655, 735), p5, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (820, 735), p6, f_pairs, fill="#ffffff", stroke_w=2, stroke_fill="#000000")

    # 8. เลข 3 ตัว (บังคับมี วิ่ง หรือ รูด)
    def gen_triple():
        base = random.choice([num1, num2])
        others = random.sample([str(i) for i in range(10)], 2)
        res = [base] + others
        random.shuffle(res)
        return "".join(res)
        
    t1_val = triple1 if triple1 and len(triple1) == 3 else gen_triple()
    t2_val = triple2 if triple2 and len(triple2) == 3 else gen_triple()
    t3_val = triple3 if triple3 and len(triple3) == 3 else gen_triple()

    f_triples = _load_font(92, font_path=text_font_path)
    draw_text_center(draw, (465, 870), t1_val, f_triples, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (655, 870), t2_val, f_triples, fill="#ffffff", stroke_w=2, stroke_fill="#000000")
    draw_text_center(draw, (845, 870), t3_val, f_triples, fill="#ffffff", stroke_w=2, stroke_fill="#000000")

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90, optimize=True)
    buf.seek(0)
    return buf.read()

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if USERS.get(username) != password:
        return templates.TemplateResponse(
            "login.html", 
            {"request": request, "error": "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง"},
            status_code=400
        )
        
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

@app.get("/", response_class=HTMLResponse)
async def lottery_page(request: Request, user: CurrentUser):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.post("/")
async def lottery_generate(
    user: CurrentUser,
    lottery_type: list[str] = Form(...),
    main1: Optional[str] = Form(None), 
    main2: Optional[str] = Form(None),
    bracket: Optional[str] = Form(None),
    den_rong: Optional[str] = Form(None),
    pair1: Optional[str] = Form(None), 
    pair2: Optional[str] = Form(None), 
    pair3: Optional[str] = Form(None), 
    pair4: Optional[str] = Form(None), 
    pair5: Optional[str] = Form(None), 
    pair6: Optional[str] = Form(None), 
    triple1: Optional[str] = Form(None),
    triple2: Optional[str] = Form(None),
    triple3: Optional[str] = Form(None),
    double1: Optional[str] = Form(None),
    double2: Optional[str] = Form(None),
    win_num: Optional[str] = Form(None), 
):
    if not lottery_type:
        raise HTTPException(status_code=400, detail="กรุณาเลือกประเภทหวยอย่างน้อย 1 รายการ")

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
        
        img_bytes = create_image_bytes(
            name_str, main1, main2, den_rong, pair1, pair2, pair3, pair4, pair5, pair6,
            triple1, triple2, triple3, double1, double2, win_num
        )
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
            
            zf.writestr(
                filename, 
                create_image_bytes(
                    name_str, main1, main2, den_rong, pair1, pair2, pair3, pair4, pair5, pair6,
                    triple1, triple2, triple3, double1, double2, win_num
                )
            )
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
