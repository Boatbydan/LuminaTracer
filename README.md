# Lumina Tracer

Language: [English](README_EN.md) | [中文](README_CN.md)

> A Web-Based Perimetry System

**Lumina Tracer** is an open-source, web-based automated perimetry system. 
This project aims to explore the possibility of using standard computer monitors for low-cost visual field screening, providing a lightweight tool for ophthalmic research and preliminary screening.

> I am someone who has been plagued by eye problems. During my long journey seeking medical help, I discovered that the limited equipment in hospitals cannot actually meet patients' needs. For example, booking a visual field test often requires waiting for days. So, can we use home devices to achieve more flexible visual field testing?
Even though the hardware foundation of electronic screens cannot compare to professional Humphrey visual field analyzers, everyone can have more time and freedom to conduct tests.
I hope to explore the potential of electronic devices in ophthalmic testing.
Darkness may have already appeared before our eyes, which makes us yearn for light even more. This is why I named it "Lumina Tracer" (Light Chaser).
---

## ✨ Key Features

Currently, it should be able to intuitively reflect whether there are visual function impairments in the screen's visible range.

* Visual field testing based on modern electronic devices
* Reference testing based on past test records

### 📊 Analysis & Reporting
* **Visual Reports**: Automatically generates sensitivity numerical maps (Sensitivity Map) and grayscale maps (Grayscale Map).

### 🖥️ User Experience
* **User Dashboard**: Complete user profile management and historical test record review.

---

## 🚀 Installation & Running

### 📥 Ready to Use (Recommended)

No need to install any code environment, you can directly download the portable version, no installation required, out of the box:

1. **Download**: Go to the [Releases page](https://github.com/Boatbydan/LuminaTracer/releases) to download `LuminaTracer.zip` for your platform.
2. **Run**: Extract the files and run **`LuminaTracer.exe`** to start.

### 📥 Compile and Run
#### 1. Environment Preparation
Ensure your system has the following environment installed:
* **Python 3.8+**
* **C++ compiler** (Windows users need to install Visual Studio Build Tools to compile C++ extensions)
> **Note**: This project is currently mainly tested in Windows 10/11 environment, compatibility testing for Linux/macOS platforms is being prepared.

#### 2. Get the Code
```bash
git clone [https://github.com/Boatbydan/LuminaTracer.git](https://github.com/Boatbydan/LuminaTracer.git)
cd LuminaTracer
```

#### 3. Installation Steps
```bash
# It is recommended to create a virtual environment (ensure python version is 3.10)
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 📖 Usage Guide
After running **Lumina Tracer**, you will enter the login/registration page.
For first-time use, you can register with any email and password you like; there is no verification mechanism. The account must be in email format.

To obtain relatively accurate reference results, please strictly follow the following physical environment requirements:

Environmental Preparation:

Keep the room dimly lit to avoid screen glare.
Keep your eyes about 50-60cm away from the screen.
Cover your right eye when testing the left eye, and vice versa.



### Operation Process:

* Register/Login: Create a profile and fill in your age (this is crucial for calculating normative deviations (TODO: deviation calculation functionality is still being improved)).
* Start Test: Select the eye and other information on the dashboard.
* Operation: Always fixate on the cross in the center of the screen. When you sense a light spot flickering in your peripheral vision, immediately press the spacebar.
* View Report: After the test is completed, the system will automatically generate an analysis report.

### Operation Process Screenshots

| Register/Login | Prepare Test | Test & Report |
|---------------|-------------|---------------|
| ![Sign Up](image/signup.jpg) | ![Prepare](image/prepare.jpg) | ![Testing](image/testing.jpg) |
| ![Sign In](image/signin.jpg) | ![Start Test](image/start_test.jpg) | ![Report](image/report.jpg) |

*Note: Images are arranged in the order of operation, from left to right, top to bottom: Sign Up → Sign In → Prepare Test → Start Test → Testing → View Report*

## 🚧 TODO
[ ] Multi-platform support
[ ] Multi-language support
[ ] Scientific calibration method
[ ] Algorithm upgrade (improve normal visual field reference)
[ ] Report tracking and analysis
[ ] Camera eye tracking
[ ] UI optimization
[ ] 30-2 mode
[ ] Other features

## ⚠️ Disclaimer
This project is for research, educational demonstration, and non-clinical preliminary screening purposes only.

Lumina Tracer is not a professional medical diagnostic technology.
Due to limitations in display brightness, ambient light, and calibration factors, test results may have deviations. If you notice vision abnormalities, visual field defects, or any eye discomfort, please go to a regular hospital for examination.

## 📄 License
This project is open source under the MIT License.
