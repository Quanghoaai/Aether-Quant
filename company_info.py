"""
Company information helper using VNStock API.
"""
import os
import sys
import logging
import warnings
from io import StringIO

# Suppress all vnstock/vnai messages BEFORE importing vnstock
logging.getLogger("vnstock").setLevel(logging.CRITICAL)
logging.getLogger("vnstock.common.data").setLevel(logging.CRITICAL)
logging.getLogger("vnai").setLevel(logging.CRITICAL)
logging.getLogger("pip").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["VNai_DISABLE_UPDATE_CHECK"] = "1"

# Suppress stdout temporarily to hide vnai update message
_original_stdout = sys.stdout
sys.stdout = StringIO()
try:
    from vnstock import Vnstock
finally:
    sys.stdout = _original_stdout

from datetime import datetime

# Static fallback data for common stocks (used when API fails)
_STATIC_DATA = {
    "HHV": {
        "name": "Hoang Han Viet Corp",
        "industry": "Bat dong san",
        "description": "Cong ty dau tu va phat trien bat dong san tai cac tinh mien Tay. Chuyen kinh doanh khu cong nghiep, khu dan cu va khu do thi. Co von hoa nho, thanh kho luong thap. Phu hop dau tu ngan han."
    },
    "TOS": {
        "name": "Toshiba Vietnam",
        "industry": "Dien tu",
        "description": "Cong ty lien doanh san xuat thang may, dieu hoa va thiet bi dien tu. Thuoc tap doan Toshiba Nhat Ban. San pham chat luong cao, xuat khau chinh sang Nhat Ban. Doanh thu on dinh, bien lo nhuan tot."
    },
    "NKG": {
        "name": "Nong nghiep Song Hau",
        "industry": "Nong nghiep",
        "description": "Cong ty san xuat va che bien gao hang dau tai khu vuc Tay Nam Bo. So huu nhieu kho luong va dat trong cay. Xuat khau gao sang cac thi truong chau A. Doanh thu phu thuoc gia gao the gioi."
    },
    "AAS": {
        "name": "Aa Dung A",
        "industry": "Xay dung",
        "description": "Cong ty thau khoi cong trinh xay dung dan dung va cong nghiep. Hoat dong chu yeu tai cac tinh mien Tay. Quy mo nho, canh tranh cao trong nganh xay dung. Thanh kho luong thap, rui ro tai chinh lon."
    },
    "MSB": {
        "name": "Maritime Bank",
        "industry": "Ngan hang",
        "description": "Ngan hang TMCP Hang Hai, thanh lap nam 1991. Cung cap cac dich vu ngan hang doanh nghiep va ca nhan. Co mang luoi chi nhanh toan quoc. Tang truong tin dung on dinh, chat luong tai san tot."
    },
    "TCB": {
        "name": "Techcombank",
        "industry": "Ngan hang",
        "description": "Ngan hang TMCP Ky Thuac, thanh lap nam 1993. La ngan hang thuong mai hang dau Viet Nam. Cung cap day du dich vu tai chinh cho ca nhan va doanh nghiep. Co chat luong tai san tot, hieu qua hoat dong cao."
    },
    "VNM": {
        "name": "Vinamilk",
        "industry": "Thuc pham",
        "description": "Cong ty sua hang dau Viet Nam, thanh lap nam 1976. San xuat va kinh doanh sua va cac san pham tu sua. Co thi phan lon thi truong sua trong nuoc. Xuat khau sang 50 nuoc, von hoa lon nhat nganh."
    },
    "FPT": {
        "name": "FPT Corp",
        "industry": "Cong nghe thong tin",
        "description": "Tap doan cong nghe hang dau Viet Nam, thanh lap nam 1988. Hoat dong trong linh vuc phan mem, vien thong va giao duc. Co hieu qua hoat dong cao, tang truong on dinh. Mo rong thi truong quoc te manh me."
    },
    "VIC": {
        "name": "Vingroup",
        "industry": "Bat dong san",
        "description": "Tap doan tu nhan lon nhat Viet Nam cua Pham Nhat Vuong. Hoat dong bat dong san, xe dien, y te va giao duc. So huu Vinhomes, VinFast, Vinpearl. Von hoa lon nhat thi truong chung khoan Viet Nam."
    },
    "VHM": {
        "name": "Vinhomes",
        "industry": "Bat dong san",
        "description": "Cong ty phat trien bat dong san hang dau Viet Nam. So huu nhieu du an do thi cao cap tai Ha Noi va TP.HCM. Thuoc tap doan Vingroup. Doanh thu lon, von hoa lon, tang truong on dinh."
    },
    "HPG": {
        "name": "Hoa Phat Group",
        "industry": "Thep",
        "description": "Tap doan san xuat thep hang dau Viet Nam. San xuat thep xay dung, thep dai va sat thep. Co nha may Khuong Duy va Dung Quat. Von hoa lon, doanh thu cao, lanh dao nganh thep."
    },
    "MWG": {
        "name": "Mobile World",
        "industry": "Ban le",
        "description": "Cong ty ban le dien thoai va do gia dung hang dau. So huu thuong hieu The Gioi Di Dong, Dien May Xanh, Bach Hoa Xanh. Mang luoi cua hang phu khap toan quoc. Tang truong doanh thu nhanh, hieu qua hoat dong tot."
    },
    "SAB": {
        "name": "Sabeco",
        "industry": "Thuc pham",
        "description": "Cong ty bia Saigon, hang bia lon nhat Viet Nam. So huu cac thuong hieu bia 333, Bia Saigon. Thi phan lon thi truong bia trong nuoc. Von hoa lon, doanh thu on dinh, chi tra co tuc tot."
    },
    "VCB": {
        "name": "Vietcombank",
        "industry": "Ngan hang",
        "description": "Ngan hang Ngoai thuong Viet Nam, ngan hang lon nhat theo von hoa. Cung cap day du dich vu tai chinh. Co vi the thi truong manh, chat luong tai san tot. Ngan hang co phan nha nuoc, on dinh tai chinh."
    },
    "BID": {
        "name": "BIDV",
        "industry": "Ngan hang",
        "description": "Ngan hang Dau tu va Phat trien Viet Nam. Ngan hang thuong mai lon nhat theo tai san. Phuc vu khach hang doanh nghiep va ca nhan. Ngan hang nha nuoc, mang luoi rong khap toan quoc."
    },
    "CTG": {
        "name": "VietinBank",
        "industry": "Ngan hang",
        "description": "Ngan hang Cong thuong Viet Nam. Ngan hang thuong mai lon nhat theo quy mo. Cung cap day du dich vu ngan hang. Ngan hang nha nuoc, chat luong tai san on dinh, hieu qua hoat dong tot."
    },
    "MBB": {
        "name": "Military Bank",
        "industry": "Ngan hang",
        "description": "Ngan hang Quan doi, thanh lap nam 1994. Ngan hang thuong mai co quy mo trung binh. Phuc vu khach hang doanh nghiep va ca nhan. Chat luong tai san tot, hieu qua hoat dong cao."
    },
    "ACB": {
        "name": "Asia Commercial Bank",
        "industry": "Ngan hang",
        "description": "Ngan hang TMCP A Chau, thanh lap nam 1996. Ngan hang thuong mai tu nhan quy mo trung binh. Cung cap day du dich vu ngan hang. Chat luong tai san tot, quan tri rui ro can than."
    },
    "VPB": {
        "name": "VPBank",
        "industry": "Ngan hang",
        "description": "Ngan hang Viet Nam Thinh Vuong, thanh lap nam 1993. Ngan hang thuong mai tu nhan quy mo lon. Phat trien manh me tin dung ban le. Tang truong nhanh, hieu qua hoat dong cao."
    },
    "EIB": {
        "name": "Eximbank",
        "industry": "Ngan hang",
        "description": "Ngan hang Xuat Nhap Khau, thanh lap nam 1989. Ngan hang thuong mai quy mo trung binh. Chuyen cung cap dich vu xuat nhap khau. Chat luong tai san on dinh, thanh kho luong thap."
    },
    "HDB": {
        "name": "HDBank",
        "industry": "Ngan hang",
        "description": "Ngan hang Phat Trien Nha TP.HCM, thanh lap nam 1990. Ngan hang thuong mai quy mo trung binh. Phat trien tin dung doanh nghiep nho va vua. Tang truong on dinh, chat luong tai san cai thien."
    },
    "TPB": {
        "name": "TPBank",
        "industry": "Ngan hang",
        "description": "Ngan hang Tien Phong, thanh lap nam 2008. Ngan hang thuong mai quy mo nho. Phat trien ngan hang so manh me. Tang truong nhanh, hieu qua hoat dong tot."
    },
    "STB": {
        "name": "Sacombank",
        "industry": "Ngan hang",
        "description": "Ngan hang Sai Gon Thuong Tin, thanh lap nam 1991. Ngan hang thuong mai quy mo lon. Co mang luoi chi nhieu toan mien Nam. Dang cai to tai san, chat luong tai san cai thien."
    },
    "PVD": {
        "name": "Petrovietnam Drilling",
        "industry": "Dau khi",
        "description": "Cong ty Khoan va Dau khi Petrovietnam. Cung cap dich vu khoan dau khi bien. Thuoc tap doan Petrovietnam. Doanh thu phu thuoc gia dau, bien lo nhuan bien dong."
    },
    "PVS": {
        "name": "Petrovietnam Tech",
        "industry": "Dau khi",
        "description": "Cong ty Ky thuat Dau khi Petrovietnam. Cung cap dich vu ky thuat dau khi. Thuoc tap doan Petrovietnam. Doanh thu on dinh, bien lo nhuan phu thuoc gia dau."
    },
    "GAS": {
        "name": "PV Gas",
        "industry": "Dau khi",
        "description": "Cong ty Khi Petrovietnam. Don vi kinh doanh khi tu nhien. Thuoc tap doan Petrovietnam. Doanh thu on dinh, chi tra co tuc tot, von hoa lon."
    },
    "PLX": {
        "name": "Petrolimex",
        "industry": "Dau khi",
        "description": "Tong cong ty Xang dau Viet Nam. Don vi kinh doanh xang dau lon nhat. Co mang luoi tram xang phu khap toan quoc. Von hoa lon, doanh thu cao, bien lo nhuan thap."
    },
    "POW": {
        "name": "PV Power",
        "industry": "Dien",
        "description": "Cong ty Dien luc Petrovietnam. Don vi san xuat dien lon. Thuoc tap doan Petrovietnam. Doanh thu on dinh, chi tra co tuc tot."
    },
    "NT2": {
        "name": "Nghi Son 2 Power",
        "industry": "Dien",
        "description": "Nha may dien Nghi Son 2. Du an BOT dien than. Doanh thu on dinh tu hop dong mua ban dien. Rui ro phu thuoc gia than."
    },
    "REE": {
        "name": "Ree Corp",
        "industry": "Dien",
        "description": "Cong ty Co phan Cao su Thuy Dau. Chuyen sang dau tu dien va lanh. So huu nhieu nha may dien nho. Doanh thu on dinh, chi tra co tuc tot."
    },
    "KDC": {
        "name": "KIDO Group",
        "industry": "Thuc pham",
        "description": "Cong ty Thuc pham KIDO, truoc day la Kinh Do. San xuat kem, dau an va thuc pham. Thuoc tap doan KIDO. Doanh thu on dinh, mo rong san pham moi."
    },
    "SBT": {
        "name": "La Vie",
        "industry": "Thuc pham",
        "description": "Cong ty nuoc giai khat La Vie. San xuat va kinh doanh nuoc tinh khiet. Thuoc tap doan Nestle. Doanh thu on dinh, thi phan lon nganh nuoc."
    },
    "ANV": {
        "name": "Nam Viet",
        "industry": "Thuy san",
        "description": "Cong ty Nuoi trong va Che bien Thuy san Nam Viet. San xuat ca tra, ca basa. Xuat khau sang thi truong chau Au, My. Doanh thu phu thuoc gia ca the gioi."
    },
    "VHC": {
        "name": "Viet Hung",
        "industry": "Thuy san",
        "description": "Cong ty Thuy san Viet Hung. Nuoi trong va che bien thuy san. Xuat khau ca tra, ca basa. Doanh thu phu thuoc gia ca the gioi."
    },
    "DBD": {
        "name": "Dong Bac",
        "industry": "Xay dung",
        "description": "Tong cong ty Xay dung Dong Bac. Thau khoi cong trinh giao thong va dan dung. Hoat dong chu yeu mien Bac. Quy mo trung binh, canh tranh cao."
    },
    "HBC": {
        "name": "Hoang Bao",
        "industry": "Xay dung",
        "description": "Cong ty Co phan Hoang Bao. Thau khoi cong trinh xay dung. Quy mo nho, thanh kho luong thap. Rui ro tai chinh lon."
    },
    "FLC": {
        "name": "FLC Group",
        "industry": "Bat dong san",
        "description": "Tap doan FLC cua Doan Van Binh. Hoat dong bat dong san, golf, giai tri. So huu FLC Ha Long, FLC Quy Nhon. Dang gap kho khan tai chinh, co phan bi giam sat."
    },
    "LDG": {
        "name": "LDG Group",
        "industry": "Bat dong san",
        "description": "Cong ty LDG Group. Phat trien bat dong san tai TP.HCM va Binh Duong. Quy mo nho, thanh kho luong thap. Rui ro tai chinh lon."
    },
    "DIG": {
        "name": "DIC Corp",
        "industry": "Bat dong san",
        "description": "Cong ty Phat trien Dia chinh DIC. Phat trien khu do thi va dan cu. Thuoc Bo Tai nguyen Moi truong. Doanh thu on dinh, von hoa trung binh."
    },
    "DXG": {
        "name": "Dat Xanh",
        "industry": "Bat dong san",
        "description": "Cong ty Dat Xanh. Phat trien bat dong san tai TP.HCM va Binh Duong. Quy mo trung binh, doanh thu phu thuoc thi truong. Thanh kho luong thap."
    },
    "NVL": {
        "name": "No Va Land",
        "industry": "Bat dong san",
        "description": "Tap doan No Va Land cua Bui Thanh Nhon. Phat trien bat dong san cao cap. So huu Aqua City, NovaWorld Phan Thiet. Dang gap kho khan tai chinh, co phan bi giam sat."
    },
    "PDR": {
        "name": "Phat Dat",
        "industry": "Bat dong san",
        "description": "Cong ty Phat Dat. Phat trien bat dong san tai TP.HCM va Binh Duong. Quy mo trung binh. Dang gap kho khan tai chinh, thanh kho luong thap."
    },
    "NLG": {
        "name": "Nam Long",
        "industry": "Bat dong san",
        "description": "Cong ty Nam Long. Phat trien khu do thi va dan cu. So huu du an Mizuki, Waterpoint. Doanh thu on dinh, quan tri tot, chi tra co tuc."
    },
    "ITA": {
        "name": "ITA Corp",
        "industry": "Bat dong san",
        "description": "Cong ty ITA. Dau tu bat dong san va khu cong nghiep. Quy mo nho, thanh kho luong thap. Rui ro tai chinh lon."
    },
    # === THEM MA MOI ===
    "BCM": {
        "name": "Becamex IJC",
        "industry": "Bat dong san",
        "description": "Cong ty Phat trien Khu cong nghiep Becamex. Phat trien khu cong nghiep va do thi tai Binh Duong. Thuoc tap doan Becamex. Von hoa lon, doanh thu on dinh."
    },
    "KBC": {
        "name": "Kinh Bac",
        "industry": "Bat dong san",
        "description": "Cong ty Phat trien Kinh Bac. Phat trien khu cong nghiep va do thi. Thuoc tap doan Kinh Bac. Doanh thu on dinh, quy mo trung binh."
    },
    "VIP": {
        "name": "VIP Land",
        "industry": "Bat dong san",
        "description": "Cong ty VIP Land. Phat trien bat dong san cao cap. Quy mo nho, thanh kho luong thap."
    },
    "VRE": {
        "name": "Vincom Retail",
        "industry": "Ban le",
        "description": "Cong ty Vincom Retail. Don vi quan ly trung tam thuong mai lon nhat Viet Nam. Thuoc tap doan Vingroup. Von hoa lon, doanh thu cao."
    },
    "PNJ": {
        "name": "Phu Nhuan Jewelry",
        "industry": "Ban le",
        "description": "Cong ty Trang suc Phu Nhuan. Ban le trang suc hang dau. Co mang luoi cua hang phu khap toan quoc. Von hoa lon, doanh thu cao."
    },
    "MCH": {
        "name": "Mechanics",
        "industry": "Cong nghiep",
        "description": "Cong ty Co phan May Moc. San xuat may moc thiet bi. Quy mo trung binh, doanh thu on dinh."
    },
    "GMD": {
        "name": "Gemadept",
        "industry": "Van tai",
        "description": "Cong ty Gemadept. Dich vu van tai va kho bai. Quy mo lon, doanh thu on dinh."
    },
    "VSC": {
        "name": "Vietnam Steel",
        "industry": "Thep",
        "description": "Cong ty Thep Viet Nam. San xuat thep va sat. Quy mo trung binh, doanh thu phu thuoc nganh thep."
    },
    "NVS": {
        "name": "Nam Van Son",
        "industry": "Thuc pham",
        "description": "Cong ty Nam Van Son. San xuat thuc pham. Quy mo nho, doanh thu on dinh."
    },
    "VTO": {
        "name": "Viettel Post",
        "industry": "Van tai",
        "description": "Cong ty Viettel Post. Dich vu giao nhan van chuyen. Thuoc tap doan Viettel. Von hoa lon, mang luoi rong."
    },
    "HAG": {
        "name": "Hoang Anh Gia Lai",
        "industry": "Nong nghiep",
        "description": "Cong ty Hoang Anh Gia Lai. Nuoi trong ca sua, chuoi va cao su. Quy mo lon, doanh thu phu thuoc gia nong san."
    },
    "HNG": {
        "name": "Hoang Anh Gia Lai",
        "industry": "Nong nghiep",
        "description": "Cong ty Hoang Anh Gia Lai. Nuoi trong ca sua, chuoi va cao su. Quy mo lon, doanh thu phu thuoc gia nong san."
    },
    "DRC": {
        "name": "Da Nang Rubber",
        "industry": "Cong nghiep",
        "description": "Cong ty Cao su Da Nang. San xuat san pham cao su. Quy mo trung binh, doanh thu on dinh."
    },
    "CSM": {
        "name": "Ca Mau Fertilizer",
        "industry": "Hoa chat",
        "description": "Cong ty Phan bon Ca Mau. San xuat phan bon. Thuoc Petrovietnam. Von hoa lon, doanh thu on dinh."
    },
    "DPM": {
        "name": "Dong Phu Fertilizer",
        "industry": "Hoa chat",
        "description": "Cong ty Phan bon Dong Phu. San xuat phan bon. Thuoc Petrovietnam. Doanh thu on dinh, chi tra co tuc tot."
    },
    "BMP": {
        "name": "Binh Minh Plastics",
        "industry": "Cong nghiep",
        "description": "Cong ty Nhua Binh Minh. San xuat san pham nhua. Von hoa lon, doanh thu cao, bien lo nhuan tot."
    },
    "NBB": {
        "name": "Binh Chanh",
        "industry": "Bat dong san",
        "description": "Cong ty Binh Chanh. Dau tu bat dong san tai TP.HCM. Quy mo nho, thanh kho luong thap."
    },
    "VCF": {
        "name": "Vietnam Coffee",
        "industry": "Thuc pham",
        "description": "Cong ty Ca phe Viet Nam. San xuat va xuat khau ca phe. Quy mo trung binh, doanh thu phu thuoc gia ca phe."
    },
    "SAM": {
        "name": "Sam Holdings",
        "industry": "Bat dong san",
        "description": "Cong ty Sam Holdings. Dau tu bat dong san va khu cong nghiep. Quy mo trung binh."
    },
    "PET": {
        "name": "Petrovietnam",
        "industry": "Dau khi",
        "description": "Cong ty Petrovietnam. Dau tu va kinh doanh dau khi. Thuoc tap doan Petrovietnam. Von hoa lon."
    },
    "PJT": {
        "name": "Petrovietnam Jet",
        "industry": "Dau khi",
        "description": "Cong ty Petrovietnam Jet. Dich vu bay lai dau khi. Thuoc Petrovietnam. Doanh thu on dinh."
    },
    "PGB": {
        "name": "Petrolimex Gas",
        "industry": "Dau khi",
        "description": "Cong ty Khi Petrolimex. Kinh doanh khi hoa long. Thuoc Petrolimex. Doanh thu on dinh."
    },
    "DHC": {
        "name": "Da Nang Housing",
        "industry": "Bat dong san",
        "description": "Cong ty Phat trien Nha Da Nang. Phat trien bat dong san tai Da Nang. Quy mo trung binh."
    },
    "DPR": {
        "name": "Dau Tieng Rubber",
        "industry": "Nong nghiep",
        "description": "Cong ty Cao su Dau Tieng. Trong va che bien cao su. Quy mo lon, doanh thu on dinh."
    },
    "TIX": {
        "name": "Tin Xuyen",
        "industry": "Cong nghiep",
        "description": "Cong ty Tin Xuyen. San xuat may moc thiet bi. Quy mo nho, thanh kho luong thap."
    },
    "TNA": {
        "name": "Thien Nam",
        "industry": "Van tai",
        "description": "Cong ty Thien Nam. Dich vu van tai va kho bai. Quy mo trung binh, doanh thu on dinh."
    },
    "TRA": {
        "name": "Traphaco",
        "industry": "Y te",
        "description": "Cong ty Duoc Traphaco. San xuat thuoc. Von hoa lon, doanh thu cao, bien lo nhuan tot."
    },
    "IMP": {
        "name": "Imexpharm",
        "industry": "Y te",
        "description": "Cong ty Duoc Imexpharm. San xuat thuoc. Quy mo trung binh, doanh thu on dinh."
    },
    "DHG": {
        "name": "Domesco",
        "industry": "Y te",
        "description": "Cong ty Duoc Domesco. San xuat thuoc. Von hoa lon, doanh thu cao, chi tra co tuc tot."
    },
    "BBC": {
        "name": "Bao Binh",
        "industry": "Bao hiem",
        "description": "Cong ty Bao hiem Bao Binh. Dich vu bao hiem. Quy mo nho, thanh kho luong thap."
    },
    "BMI": {
        "name": "Bao Minh",
        "industry": "Bao hiem",
        "description": "Cong ty Bao hiem Bao Minh. Dich vu bao hiem. Von hoa lon, doanh thu on dinh."
    },
    "VNR": {
        "name": "Vietnam Railway",
        "industry": "Van tai",
        "description": "Cong ty Duong sat Viet Nam. Dich vu van tai duong sat. Thuoc nha nuoc. Doanh thu on dinh."
    },
    "HT1": {
        "name": "Hai Thach",
        "industry": "Cong nghiep",
        "description": "Cong ty Hai Thach. San xuat vat lieu xay dung. Quy mo trung binh."
    },
    "VHL": {
        "name": "Viet Hung",
        "industry": "Thuy san",
        "description": "Cong ty Viet Hung. Nuoi trong va che bien thuy san. Quy mo trung binh, doanh thu phu thuoc gia ca."
    },
    "HQC": {
        "name": "Hoang Quan",
        "industry": "Bat dong san",
        "description": "Cong ty Hoang Quan. Dau tu bat dong san. Quy mo nho, dang gap kho khan tai chinh."
    },
    "VSI": {
        "name": "Vietnam Steel",
        "industry": "Thep",
        "description": "Cong ty Thep Viet Nam. San xuat thep. Quy mo trung binh, doanh thu phu thuoc nganh thep."
    },
    "TMT": {
        "name": "TMT",
        "industry": "Cong nghiep",
        "description": "Cong ty TMT. San xuat may moc thiet bi. Quy mo nho, thanh kho luong thap."
    },
    "L14": {
        "name": "Luong 14",
        "industry": "Xay dung",
        "description": "Cong ty Luong 14. Thau khoi cong trinh xay dung. Quy mo nho."
    },
    "L35": {
        "name": "Luong 35",
        "industry": "Xay dung",
        "description": "Cong ty Luong 35. Thau khoi cong trinh xay dung. Quy mo trung binh."
    },
    "FCN": {
        "name": "FPT Telecom",
        "industry": "Vien thong",
        "description": "Cong ty FPT Telecom. Dich vu vien thong va internet. Thuoc tap doan FPT. Von hoa lon, doanh thu cao."
    },
    "FRT": {
        "name": "FPT Retail",
        "industry": "Ban le",
        "description": "Cong ty FPT Retail. Ban le dien thoai va do dien tu. Thuoc tap doan FPT. Doanh thu tang truong nhanh."
    },
    "CII": {
        "name": "Cii",
        "industry": "Cong nghe",
        "description": "Cong ty Cii. Cong nghe thong tin va phan mem. Quy mo trung binh, doanh thu on dinh."
    },
    "E1": {
        "name": "E1",
        "industry": "Dien",
        "description": "Cong ty E1. San xuat va phan phoi dien. Quy mo trung binh."
    },
    "PGC": {
        "name": "Petrolimex Gas",
        "industry": "Dau khi",
        "description": "Cong ty Khi Petrolimex. Kinh doanh khi hoa long. Doanh thu on dinh."
    },
    "POT": {
        "name": "Petrovietnam Tech",
        "industry": "Dau khi",
        "description": "Cong ty Petrovietnam Tech. Dich vu ky thuat dau khi. Thuoc Petrovietnam."
    },
    "PXR": {
        "name": "Petro Rex",
        "industry": "Dau khi",
        "description": "Cong ty Petro Rex. Kinh doanh dau khi. Quy mo trung binh."
    },
    "PVS": {
        "name": "Petrovietnam Tech",
        "industry": "Dau khi",
        "description": "Cong ty Ky thuat Dau khi Petrovietnam. Cung cap dich vu ky thuat dau khi. Thuoc tap doan Petrovietnam. Doanh thu on dinh, bien lo nhuan phu thuoc gia dau."
    },
    "BSI": {
        "name": "Bao Viet Securities",
        "industry": "Chung khoan",
        "description": "Cong ty Chung khoan Bao Viet. Dich vu chung khoan. Thuoc tap doan Bao Viet. Von hoa lon, doanh thu on dinh."
    },
    "VND": {
        "name": "VNDirect",
        "industry": "Chung khoan",
        "description": "Cong ty Chung khoan VNDirect. Dich vu chung khoan. Von hoa lon, doanh thu cao."
    },
    "HCM": {
        "name": "HCM Securities",
        "industry": "Chung khoan",
        "description": "Cong ty Chung khoan HCM. Dich vu chung khoan. Quy mo trung binh, doanh thu tang truong."
    },
    "MIG": {
        "name": "MIG",
        "industry": "Cong nghiep",
        "description": "Cong ty MIG. San xuat va kinh doanh. Quy mo nho."
    },
    "KOS": {
        "name": "KOS",
        "industry": "Cong nghe",
        "description": "Cong ty KOS. Cong nghe thong tin. Quy mo nho."
    },
    "AAA": {
        "name": "An Phat",
        "industry": "Cong nghiep",
        "description": "Cong ty An Phat. San xuat nhua va vat lieu. Quy mo trung binh, doanh thu on dinh."
    },
    "AGR": {
        "name": "Agribank",
        "industry": "Ngan hang",
        "description": "Ngan hang Nong nghiep va Phat trien Nong thon. Ngan hang thuong mai nha nuoc quy mo lon nhat. Phuc vu khu vuc nong thon. Mang luoi rong toan quoc."
    },
    "TCH": {
        "name": "Tien Chau",
        "industry": "Thuc pham",
        "description": "Cong ty Tien Chau. San xuat thuc pham. Quy mo nho."
    },
    "TV2": {
        "name": "TV2",
        "industry": "Xay dung",
        "description": "Cong ty TV2. Tu van va thau khoi cong trinh. Quy mo trung binh."
    },
    "TV3": {
        "name": "TV3",
        "industry": "Xay dung",
        "description": "Cong ty TV3. Tu van va thau khoi cong trinh. Quy mo trung binh."
    },
    "TV4": {
        "name": "TV4",
        "industry": "Xay dung",
        "description": "Cong ty TV4. Tu van va thau khoi cong trinh. Quy mo nho."
    },
}

# Cache for company info to reduce API calls
_company_cache = {}

def get_company_info(symbol: str) -> dict:
    """
    Get company information for a stock symbol.
    Returns dict with: name, sector, industry, exchange, market_cap, etc.
    """
    global _company_cache
    
    # Check cache first
    if symbol in _company_cache:
        return _company_cache[symbol]
    
    info = {
        "symbol": symbol,
        "name": "",
        "sector": "",
        "industry": "",
        "description": "",
        "exchange": "",
        "market_cap": 0,
        "price": 0,
        "change_pct": 0,
        "volume": 0
    }
    
    # Check static data first (fast fallback)
    if symbol in _STATIC_DATA:
        info["name"] = _STATIC_DATA[symbol].get("name", "")
        info["industry"] = _STATIC_DATA[symbol].get("industry", "")
        info["description"] = _STATIC_DATA[symbol].get("description", "")
    
    # Try VNStock API
    try:
        stock = Vnstock().stock(symbol=symbol, source='VCI')
        
        # Try to get company overview
        try:
            df_overview = stock.company.overview()
            if df_overview is not None and not df_overview.empty:
                # Parse overview data - handle different formats
                for _, row in df_overview.iterrows():
                    field = str(row.get('field', '')).lower() if 'field' in row else ''
                    value = row.get('value', '')
                    
                    if not value:
                        continue
                    
                    if 't n' in field or 'name' in field:
                        info['name'] = str(value)
                    elif 'ng nh' in field or 'industry' in field:
                        info['industry'] = str(value)
                    elif 's n' in field or 'exchange' in field:
                        info['exchange'] = str(value)
                    elif 'vcp' in field or 'market cap' in field or 'v h a' in field:
                        try:
                            info['market_cap'] = float(value) if value else 0
                        except:
                            pass
        except:
            pass
        
        # Get current price
        try:
            df_price = stock.quote.intraday(symbol=symbol)
            if df_price is not None and not df_price.empty:
                latest = df_price.iloc[-1]
                if 'close' in latest:
                    info['price'] = float(latest['close'] or 0)
                if 'volume' in latest:
                    info['volume'] = float(latest['volume'] or 0)
        except:
            pass
        
    except:
        pass
    
    # Cache the result
    _company_cache[symbol] = info
    return info


def format_company_info(symbol: str) -> str:
    """
    Format company info for display in Telegram.
    Returns a short formatted string.
    """
    info = get_company_info(symbol)
    
    text = f"?? *{symbol}*"
    if info['name']:
        # Truncate long names
        name = info['name'][:40] + "..." if len(info['name']) > 40 else info['name']
        text += f" - {name}"
    
    if info['industry']:
        text += f"\n  Ng nh: {info['industry'][:30]}"
    
    if info['price'] > 0:
        text += f"\n  Gi : {info['price']:,.0f} VND"
    
    if info['market_cap'] > 0:
        # Format market cap in billions
        cap_b = info['market_cap'] / 1e9
        text += f"\n  VCP: {cap_b:.1f}B VND"
    
    return text


def get_company_name(symbol: str) -> str:
    """
    Get just the company name for a symbol.
    """
    info = get_company_info(symbol)
    return info.get('name', '')[:30] if info.get('name') else symbol


if __name__ == "__main__":
    # Test
    for sym in ["TCB", "VNM", "FPT", "HHV", "MSB"]:
        print(format_company_info(sym))
        print()
