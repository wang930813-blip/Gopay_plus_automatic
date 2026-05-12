# GoPay Plus 自动订阅机

全自动 ChatGPT Plus 订阅工具。

你只需要提供一个 ChatGPT 的 access_token，本工具会自动完成整个 GoPay 付款流程，20 秒内激活 Plus 会员。

不建议没有基础的用户自己部署，请使用gpt和claude的高级模型进行部署，根据需要具体选择场景和改造项目。
本项目 的订阅链路百分百可行，已实践，具体的风控场景是对虚拟号码，即最后一步付款的风控，触发了反欺骗拦截。有其他问题和错误，请找ai分析！

注意：截止到2026年5.12日12时，单个gopay号多绑plus已行不通，目前已知最多绑定1-3个，可根据具体场景选择，
一号一绑则无需注册whatsapp，直接注册gopay或者gojek，订阅过程中输入sms验证码即可。 
一号多绑，则可在虚拟手机号期限内，注册gopay，gojek后多次接码 多次绑定即可，也可注册whatsapp，封号风险较大

作者未尝试过sms api接码和批量接码，但是原理一致，都是可行的，需要用户自己改造smsapi接码的部分，仅提供了参考。

本项目为免费开源，收费售卖者死冯，有问题请联系邮箱links-to@outlook.com 作者不负责任何用户的行为，该项目仅供学习交流。
---

## 它能做什么

- 输入一个 ChatGPT access_token
- 自动创建 IDR（印尼盾）订阅订单
- 自动通过 Stripe + Midtrans + GoPay 完成付款
- 自动接收并填写 OTP 验证码
- 自动输入 GoPay PIN
- 自动验证订阅状态
- 最终结果：该账号变成 ChatGPT Plus（0 元首月试用）

整个过程约 20 秒，全程无需人工干预（配置好之后）。

---

## 你需要准备什么

| 项目 | 说明 | 如何获取 |
|------|------|---------|
| Linux 服务器 | 推荐 Debian/Ubuntu，1核1G即可 | 任意云服务商 |
| Python 3.10+ | 运行支付核心和编排器 | apt install python3 |
| Node.js 18+ | 仅 WhatsApp 模式需要 | apt install nodejs |
| SOCKS5 代理 | 日本/东南亚出口 IP | 自建或购买 |
| GoPay 账号 | 印尼手机号 + 6 位 PIN | 用印尼虚拟号注册 Gojek |
| ChatGPT access_token | 要订阅的账号的凭证 | 见下方获取方法 |
gopay使用必须开启pin，否则将无法支付。

### 如何获取 access_token

1. 用浏览器登录 https://chatgpt.com
2. 登录后，在地址栏输入：https://chatgpt.com/api/auth/session
3. 页面会显示一段 JSON，找到 "accessToken" 字段
4. 复制它的值（以 eyJ 开头的一长串字符，通常 1000+ 字符）
5. 这就是 access_token

注意：access_token 有效期约 24 小时，过期需要重新获取。

### 如何注册 GoPay 账号

1. 在接码平台（如 HeroSMS、5sim）购买一个印尼手机号
2. 下载 Gojek APP（或用模拟器）
3. 用该印尼号注册 Gojek 账号
4. 注册过程中会收到 SMS 验证码（从接码平台获取）
5. 设置 GoPay PIN（6 位数字，建议所有号统一设同一个 PIN）
6. 注册完成后，记录：手机号 + PIN

如果你要批量订阅，重复上述步骤注册多个 GoPay 号即可。

---

## 架构说明

本项目由 3 个服务组成：

```
                    用户请求
                       |
                       v
+--------------------------------------------------+
| orchestrator（编排器）                            |
| 监听 :8800 端口                                  |
| 接收 /subscribe 请求，协调整个流程               |
+--------------------------------------------------+
        |                           |
        v                           v
+-------------------+    +-------------------+
| plus_gopay_links  |    | OTP 来源          |
| 支付核心          |    | (三选一)          |
| gRPC :50051       |    |                   |
| 执行 15 步付款    |    | 1. 手动/ADB推送   |
|                   |    | 2. 接码平台API    |
|                   |    | 3. WhatsApp       |
+-------------------+    +-------------------+
```

你不需要理解内部细节，只需要：
1. 配置好 config.json
2. 启动服务
3. 发 HTTP 请求

---

## 安装步骤（从零开始）

### 第一步：准备服务器

```bash
# 以 root 登录你的 Linux 服务器

# 更新系统
apt update && apt upgrade -y

# 安装 Python 3 和 pip
apt install -y python3 python3-pip curl

# 安装 Node.js 18（仅 WhatsApp 模式需要，否则跳过）
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs
```

### 第二步：下载项目

```bash
# 把项目放到 /opt/gopay-plus（或任意目录）
cd /opt
git clone <你的仓库地址> gopay-plus
cd gopay-plus
```

### 第三步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

如果报错 "externally-managed-environment"，加 --break-system-packages：

```bash
pip install --break-system-packages -r requirements.txt
```

### 第四步：安装 Node.js 依赖（仅 WhatsApp 模式）

```bash
cd to_whatsapp && npm install && cd ..
```

### 第五步：配置

```bash
cp config.example.json config.json
nano config.json   # 或用 vim 编辑
```

config.json 各字段说明：

```json
{
  "gopay": {
    "country_code": "62",
    // 说明：印尼国家码，固定填 62

    "phone_number": "81234567890",
    // 说明：你的 GoPay 手机号，不含国家码
    // 如果你用多号模式，这里填默认号，每次请求可覆盖

    "pin": "123456",
    // 说明：你的 GoPay 6 位 PIN
    // 批量模式建议所有号设同一个 PIN

    "browser_locale": "zh-CN",
    // 说明：浏览器语言，一般不用改

    "pin_locale": "id"
    // 说明：PIN 页面语言，固定 id（印尼语）
  },

  "proxy": "socks5://127.0.0.1:1080",
  // 说明：SOCKS5 代理地址
  // 必须是日本或东南亚出口 IP
  // 如果代理在本机，填 127.0.0.1:端口
  // 如果在其他服务器，填 IP:端口

  "orchestrator": {
    "port": 8800,
    // 说明：编排器监听端口

    "otp_timeout": 90,
    // 说明：等待 OTP 的最大秒数，超时则失败

    "auth_token": "my-secret-token-123"
    // 说明：API 访问密钥，防止未授权调用
    // 自己随便设一个随机字符串
    // 调用 /subscribe 时需要在 Header 带上：Authorization: Bearer my-secret-token-123
  },

  "otp": {
    "mode": "manual",
    // 说明：OTP 接收模式，三选一：
    //   "manual"   - 手动输入或 ADB 自动转发
    //   "sms_api"  - 接码平台 API 自动获取
    //   "whatsapp" - WhatsApp 自动接收

    "sms_api": {
      "provider": "herosms",
      // 说明：接码平台名称（仅做标记，不影响逻辑）

      "api_key": "",
      // 说明：接码平台的 API Key

      "base_url": "https://api.herosms.com",
      // 说明：接码平台的 API 地址

      "country": "id",
      // 说明：国家代码

      "service": "gopay",
      // 说明：服务名称

      "poll_interval_sec": 3,
      // 说明：每隔几秒查询一次

      "poll_timeout_sec": 90
      // 说明：最多查询多少秒
    },

    "whatsapp": {
      "grpc_addr": "127.0.0.1:50056"
      // 说明：WhatsApp Relay 的 gRPC 地址
    }
  }
}
```

注意：JSON 不支持注释，实际使用时删掉所有 // 开头的行。

### 第六步：启动

一键启动：

```bash
chmod +x start.sh
./start.sh
```

或手动启动（方便调试）：

```bash
# 终端 1：启动支付核心
cd plus_gopay_links
python3 payment_server.py --config ../config.json --listen :50051

# 终端 2：启动编排器
cd /opt/gopay-plus
python3 orchestrator.py

# 终端 3（仅 WhatsApp 模式）：启动 WhatsApp Relay
cd to_whatsapp
WA_PAIRING_PHONE=6281234567890 WA_PROXY_URL=socks5://127.0.0.1:1080 WA_GRPC_PORT=50056 node index.js
```

### 第七步：验证服务正常

```bash
curl http://localhost:8800/health
```

应该返回：

```json
{"ok": true, "service": "gopay-plus", "otp_mode": "manual"}
```

---

## 使用方法

### 基本用法（单次订阅）

```bash
curl -X POST http://localhost:8800/subscribe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-token-123" \
  -d '{"session_token": "eyJhbGciOiJSUzI1NiIs..."}'
```

成功返回：

```json
{"ok": true, "charge_ref": "A120260512035748B2ex55ZFzbID", "elapsed_ms": 19928}
```

失败返回：

```json
{"ok": false, "error": "otp_timeout", "detail": "timeout waiting for OTP after 90s", "elapsed_ms": 91000}
```

### 多号用法（每次指定不同手机号）

```bash
curl -X POST http://localhost:8800/subscribe \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer my-secret-token-123" \
  -d '{
    "session_token": "eyJ...",
    "phone_number": "82222222222",
    "pin": "123456"
  }'
```

phone_number 和 pin 是可选参数，不传则使用 config.json 中的默认值。

---

## OTP 接收方案详解

这是最关键的部分。GoPay 在付款过程中会发一个 6 位验证码到你的手机，你需要把这个验证码传给本工具。

有三种方式，根据你的场景选择：

---

### 方案一：manual 模式（手动输入）

最简单，适合新手调试和少量使用。

原理：你自己看到验证码后，手动发一个 HTTP 请求把验证码告诉编排器。

设置：config.json 中 otp.mode 设为 "manual"

使用流程：

```
1. 你发起 /subscribe 请求
2. 等约 10 秒，GoPay 会发验证码到你手机（SMS 或 WhatsApp）
3. 你看到验证码后，在 90 秒内执行：
   curl -X POST http://服务器:8800/otp -d '{"otp": "123456"}'
4. 编排器收到验证码，自动完成后续步骤
5. 返回订阅结果
```

如果你有 Android 模拟器（MuMu、雷电等），可以用 otp_forwarder.py 自动化这一步：

```bash
# 修改 otp_forwarder.py 顶部的配置：
# OTP_URL = "http://你的服务器IP:8800/otp"
# AUTH = "Bearer my-secret-token-123"

# 确保 ADB 连接正常
adb connect 127.0.0.1:7555
adb devices

# 启动自动转发（保持窗口开着）
python3 otp_forwarder.py
```

这样只要模拟器里的 WhatsApp 收到验证码通知，脚本就会自动转发给编排器。

重要：不要点开 WhatsApp 的通知消息，否则 ADB 抓不到。

---

### 方案二：sms_api 模式（接码平台自动获取）

适合批量生产，全自动无人值守。

原理：GoPay 发 SMS 验证码到虚拟手机号，编排器自动调接码平台 API 查询并获取验证码。

设置：

1. 在接码平台注册账号，充值，获取 API Key
2. config.json 中 otp.mode 设为 "sms_api"
3. 填写 sms_api 配置（api_key、base_url）

对接你的接码平台：

编排器默认会请求这个 URL：

```
GET {base_url}?action=get_sms&api_key={你的key}&phone={手机号}&country=id
```

然后从响应中提取 6 位数字。

如果你的接码平台 URL 格式不同，编辑 orchestrator.py 中的 _wait_sms_api_otp 函数，修改 url 那一行即可。响应解析是通用的（自动从任何文本/JSON 中提取 6 位数字）。

常见接码平台 API 格式：

```
HeroSMS:
  GET https://api.herosms.com/api/get_sms?api_key=KEY&phone=PHONE
  返回：{"sms": "Your verification code is 123456"}

5sim:
  GET https://5sim.net/v1/user/check/{order_id}
  Header: Authorization: Bearer KEY
  返回：{"sms": [{"text": "123456 is your code"}]}

sms-activate:
  GET https://api.sms-activate.org/stubs/handler_api.php?api_key=KEY&action=getStatus&id=ORDER_ID
  返回：STATUS_OK:123456
```

批量使用流程：

```
1. 在接码平台买一个印尼号（如 81234567890）
2. 用这个号注册 GoPay（设 PIN 为 123456）
3. 调用 /subscribe，传入这个号：
   curl -X POST http://localhost:8800/subscribe \
     -d '{"session_token": "eyJ...", "phone_number": "81234567890", "pin": "123456"}'
4. 编排器自动从接码平台拿到验证码，完成订阅
5. 换下一个号 + 下一个 access_token，重复
```

---

### 方案三：whatsapp 模式（WhatsApp 自动接收）

适合固定一个 GoPay 号长期使用。

原理：在服务器上登录 WhatsApp，自动监听 GoPay 发来的验证码消息。

设置：

1. config.json 中 otp.mode 设为 "whatsapp"
2. 启动 WhatsApp Relay 服务

首次配对步骤：

```bash
cd to_whatsapp
export WA_PAIRING_PHONE=6281234567890   # 你的手机号（含国家码62）
export WA_PROXY_URL=socks5://127.0.0.1:1080
export WA_GRPC_PORT=50056
node index.js
```

启动后终端会显示一个 8 位配对码（如 WN2XQNLB）。

在你的手机上操作：
1. 打开 WhatsApp
2. 点右上角三个点 -> 已关联设备
3. 点"关联设备"
4. 输入终端显示的 8 位配对码

配对成功后，服务会持续运行，自动接收验证码。

已知问题：WhatsApp 可能对金融类消息（如 GoPay 验证码）做屏蔽处理（MASK_LINKED_DEVICES），导致关联设备收不到。如果遇到这个问题，请改用 manual 或 sms_api 模式。

---

### 三种方案对比

| | manual | sms_api | whatsapp |
|---|---|---|---|
| 全自动 | 需手动或ADB脚本 | 完全自动 | 完全自动 |
| 多号支持 | 支持 | 支持 | 仅单号 |
| 额外成本 | 无 | 接码平台费用 | 无 |
| 稳定性 | 取决于人/ADB | 高 | 可能被屏蔽 |
| 适合场景 | 调试/少量 | 批量生产 | 固定号长期 |

---

## 生产部署（systemd 自启动）

让服务开机自动启动、崩溃自动重启：

```bash
# 创建服务文件
cat > /etc/systemd/system/plus-gopay-links.service << 'EOF'
[Unit]
Description=GoPay Payment Service
After=network.target
[Service]
Type=simple
WorkingDirectory=/opt/gopay-plus
ExecStart=/usr/bin/python3 plus_gopay_links/payment_server.py --config config.json --listen :50051
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/gopay-orchestrator.service << 'EOF'
[Unit]
Description=GoPay Orchestrator
After=plus-gopay-links.service
[Service]
Type=simple
WorkingDirectory=/opt/gopay-plus
ExecStart=/usr/bin/python3 orchestrator.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
[Install]
WantedBy=multi-user.target
EOF

# 启用并启动
systemctl daemon-reload
systemctl enable plus-gopay-links gopay-orchestrator
systemctl start plus-gopay-links gopay-orchestrator

# 查看状态
systemctl status plus-gopay-links
systemctl status gopay-orchestrator

# 查看日志
journalctl -u gopay-orchestrator -f
```

---

## 常见问题

### Q: 返回 otp_timeout（OTP 超时）

原因：90 秒内没收到验证码。

排查：
- manual 模式：你是否在 90 秒内推送了 /otp？
- sms_api 模式：接码平台 API 是否配置正确？手机号是否已激活？
- whatsapp 模式：WhatsApp Relay 是否在运行？是否被 MASK_LINKED_DEVICES 屏蔽？

### Q: 返回 start_gopay_failed

原因：access_token 无效或已过期。

解决：重新从 chatgpt.com/api/auth/session 获取新的 access_token。

### Q: PIN 验证失败（465 错误）

原因：
- PIN 不是 6 位数字
- 短时间内多次输错 PIN，被 GoPay 临时锁定（冷却期 1 小时）

解决：确认 PIN 正确，等 1 小时后重试。

### Q: Midtrans charge 被拒（fraud_status=deny）

原因：同一个 GoPay 号短时间内做了太多次 linking 操作，触发了 Midtrans 反欺诈。

解决：
- 正常使用不会触发（一个号只订阅一次）
- 如果是调试导致的，等几小时后自动恢复
- 批量模式下用不同号，不会有这个问题

### Q: 如何同时订阅多个账号？

可以并发发送多个 /subscribe 请求，每个传不同的 session_token 和 phone_number。编排器支持并发处理。

但注意：如果用 manual 模式，多个并发请求的 OTP 可能会混淆。建议批量场景使用 sms_api 模式。

### Q: 代理有什么要求？

- 必须是 SOCKS5 协议
- 出口 IP 必须是日本或东南亚（印尼最佳）
- 不能是被 GoPay/Midtrans 封禁的 IP
- 推荐自建代理或使用住宅代理

---

## 项目结构

```
gopay-plus/
|-- README.md              # 本文件
|-- config.example.json    # 配置模板（复制为 config.json 使用）
|-- requirements.txt       # Python 依赖列表
|-- start.sh               # 一键启动脚本
|-- orchestrator.py        # 编排器（HTTP API + OTP 管理）
|-- otp_forwarder.py       # ADB OTP 自动转发脚本
|-- .gitignore             # Git 忽略规则
|-- plus_gopay_links/      # 支付核心模块
|   |-- gopay.py           # 15 步 GoPay 支付流程实现
|   |-- payment_server.py  # gRPC 服务端
|   |-- requirements.txt   # 模块依赖
|   |-- proto/             # gRPC 协议定义
|   |   |-- payment.proto
|   |   +-- otp.proto
|   |-- payment_pb2.py     # 自动生成的 proto 代码
|   |-- payment_pb2_grpc.py
|   |-- otp_pb2.py
|   +-- otp_pb2_grpc.py
+-- to_whatsapp/           # WhatsApp OTP 接收模块（可选）
    |-- index.js           # WhatsApp 客户端主程序
    |-- package.json       # Node.js 依赖
    |-- wa_relay.py        # Node 进程管理
    +-- proto/
        +-- otp.proto
```

---

## 免责声明

本项目仅供学习研究使用。使用者需自行承担风险，遵守相关服务条款。 不得违法openai的条款和相关法律法规，使用则默认用户知情，一切后果由用户个人承担，与作者无关。
