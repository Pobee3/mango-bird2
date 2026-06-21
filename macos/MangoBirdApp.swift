import Cocoa
import CoreGraphics
import Network
import WebKit

private let mangoSystemPrompt = """
你叫 Mango，是一只芒果青色小鸟，也是一个友好、可靠的中文知识助手。当需要自称时，只用 Mango，不要用小鸟、我这只小鸟等其他自称。优先直接回答用户的临时知识问题，内容准确、清楚、简洁。不知道或不确定时明确说明，不编造来源。默认使用中文，除非用户要求其他语言。保留一点温柔可爱的语气，但不要让语气妨碍信息表达。回答使用自然纯文本，不使用 Markdown 加粗、标题、表格或代码块，除非用户明确要求。尤其不要输出 ** 这类加粗标记。大多数普通回答不使用表情符号；只在鼓励、安慰、庆祝或轻松闲聊等确实合适的场景偶尔使用一个。不要每次固定使用表情，不要连续多轮重复相同表情，也不要堆叠多个表情。
"""

private struct MangoProvider {
  let label: String
  let apiURL: String
  let model: String
}

private let mangoProviders: [String: MangoProvider] = [
  "deepseek": MangoProvider(
    label: "DeepSeek",
    apiURL: "https://api.deepseek.com/chat/completions",
    model: "deepseek-v4-flash"
  ),
  "glm": MangoProvider(
    label: "GLM",
    apiURL: "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    model: "glm-4-flash"
  )
]

private struct MangoHTTPRequest {
  let method: String
  let path: String
  let headers: [String: String]
  let body: Data
}

private final class MangoLocalServer {
  private let resourceURL: URL
  private let configURL: URL
  private let queue = DispatchQueue(label: "app.mango-bird.local-server")
  private var listener: NWListener?
  private var environment: [String: String]

  init(resourceURL: URL, configURL: URL, environment: [String: String]) {
    self.resourceURL = resourceURL
    self.configURL = configURL
    self.environment = environment
  }

  func start(completion: @escaping (Result<URL, Error>) -> Void) {
    do {
      let parameters = NWParameters.tcp
      parameters.requiredLocalEndpoint = .hostPort(host: "127.0.0.1", port: .any)
      let listener = try NWListener(using: parameters)
      listener.newConnectionHandler = { [weak self] connection in
        self?.handle(connection: connection)
      }
      listener.stateUpdateHandler = { state in
        switch state {
        case .ready:
          guard let port = listener.port,
                let url = URL(string: "http://127.0.0.1:\(port.rawValue)/mango-bird.html?desktop=1")
          else { return }
          DispatchQueue.main.async {
            completion(.success(url))
          }
        case .failed(let error):
          DispatchQueue.main.async {
            completion(.failure(error))
          }
        default:
          break
        }
      }
      self.listener = listener
      listener.start(queue: queue)
    } catch {
      completion(.failure(error))
    }
  }

  func stop() {
    listener?.cancel()
    listener = nil
  }

  private func handle(connection: NWConnection) {
    connection.start(queue: queue)
    receive(on: connection, buffer: Data())
  }

  private func receive(on connection: NWConnection, buffer: Data) {
    connection.receive(minimumIncompleteLength: 1, maximumLength: 64 * 1024) { [weak self] data, _, isComplete, error in
      guard let self else { return }
      if error != nil || isComplete {
        connection.cancel()
        return
      }
      var nextBuffer = buffer
      if let data {
        nextBuffer.append(data)
      }
      if let request = self.parseRequest(nextBuffer) {
        self.route(request) { response in
          connection.send(content: response, completion: .contentProcessed { _ in
            connection.cancel()
          })
        }
      } else if nextBuffer.count > 512 * 1024 {
        connection.send(content: self.jsonResponse(status: 413, payload: ["error": "请求内容过长。"]), completion: .contentProcessed { _ in
          connection.cancel()
        })
      } else {
        self.receive(on: connection, buffer: nextBuffer)
      }
    }
  }

  private func parseRequest(_ data: Data) -> MangoHTTPRequest? {
    guard let marker = data.range(of: Data("\r\n\r\n".utf8)) else { return nil }
    let headerData = data[..<marker.lowerBound]
    guard let headerText = String(data: headerData, encoding: .utf8) else { return nil }
    let lines = headerText.components(separatedBy: "\r\n")
    guard let requestLine = lines.first else { return nil }
    let parts = requestLine.split(separator: " ", maxSplits: 2).map(String.init)
    guard parts.count >= 2 else { return nil }

    var headers: [String: String] = [:]
    for line in lines.dropFirst() {
      guard let separator = line.firstIndex(of: ":") else { continue }
      let key = String(line[..<separator]).trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
      let value = String(line[line.index(after: separator)...]).trimmingCharacters(in: .whitespacesAndNewlines)
      headers[key] = value
    }

    let bodyStart = marker.upperBound
    let contentLength = Int(headers["content-length"] ?? "0") ?? 0
    guard data.count >= bodyStart + contentLength else { return nil }
    let body = data[bodyStart..<(bodyStart + contentLength)]
    return MangoHTTPRequest(method: parts[0], path: parts[1], headers: headers, body: Data(body))
  }

  private func route(_ request: MangoHTTPRequest, completion: @escaping (Data) -> Void) {
    let cleanPath = request.path.split(separator: "?", maxSplits: 1).first.map(String.init) ?? request.path
    if request.method == "GET", cleanPath == "/api/health" {
      completion(healthResponse())
      return
    }
    if request.method == "POST", cleanPath == "/api/config" {
      completion(handleConfig(request.body))
      return
    }
    if request.method == "POST", cleanPath == "/api/chat" {
      handleChat(request.body, completion: completion)
      return
    }
    if request.method == "POST", cleanPath == "/api/parse-reminder" {
      handleParseReminder(request.body, completion: completion)
      return
    }
    if request.method == "GET" || request.method == "HEAD" {
      completion(staticResponse(path: cleanPath, includeBody: request.method == "GET"))
      return
    }
    completion(jsonResponse(status: 404, payload: ["error": "接口不存在。"]))
  }

  private func configuredProvider() -> String {
    let provider = (environment["MANGO_AI_PROVIDER"] ?? "deepseek").trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    return mangoProviders[provider] == nil ? "deepseek" : provider
  }

  private func configuredAPIKey() -> String {
    environment["MANGO_AI_API_KEY"] ?? environment["DEEPSEEK_API_KEY"] ?? ""
  }

  private func configuredAPIURL(provider: String) -> String {
    environment["MANGO_AI_API_URL"]
      ?? environment["DEEPSEEK_API_URL"]
      ?? mangoProviders[provider]?.apiURL
      ?? mangoProviders["deepseek"]!.apiURL
  }

  private func configuredModel(provider: String) -> String {
    environment["MANGO_AI_MODEL"]
      ?? environment["DEEPSEEK_MODEL"]
      ?? mangoProviders[provider]?.model
      ?? mangoProviders["deepseek"]!.model
  }

  private func configuredMode() -> String {
    let mode = environment["MANGO_AI_MODE"] ?? environment["DEEPSEEK_MODE"] ?? "fast"
    return ["fast", "thinking"].contains(mode) ? mode : "fast"
  }

  private func healthResponse() -> Data {
    let provider = configuredProvider()
    let providers = mangoProviders.keys.sorted().map { key in
      ["id": key, "label": mangoProviders[key]!.label]
    }
    return jsonResponse(status: 200, payload: [
      "ok": true,
      "configured": !configuredAPIKey().isEmpty,
      "provider": provider,
      "providers": providers,
      "model": configuredModel(provider: provider),
      "mode": configuredMode()
    ])
  }

  private func handleConfig(_ body: Data) -> Data {
    guard body.count > 0, body.count <= 4096 else {
      return jsonResponse(status: 413, payload: ["error": "API Key 内容过长。"])
    }
    guard let payload = try? JSONSerialization.jsonObject(with: body) as? [String: Any] else {
      return jsonResponse(status: 400, payload: ["error": "请求格式不正确。"])
    }
    let provider = payload["provider"] as? String ?? "deepseek"
    guard mangoProviders[provider] != nil else {
      return jsonResponse(status: 400, payload: ["error": "请选择可用的模型服务。"])
    }
    guard var apiKey = payload["apiKey"] as? String ?? payload["deepseekApiKey"] as? String else {
      return jsonResponse(status: 400, payload: ["error": "请输入 API Key。"])
    }
    apiKey = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
    if apiKey.contains("\n") || apiKey.contains("\r") {
      return jsonResponse(status: 400, payload: ["error": "API Key 不能包含换行，请重新粘贴。"])
    }
    if apiKey.count < 12 {
      return jsonResponse(status: 400, payload: ["error": "API Key 看起来太短，请检查后再保存。"])
    }

    do {
      try FileManager.default.createDirectory(at: configURL, withIntermediateDirectories: true)
      let model = mangoProviders[provider]!.model
      let envURL = configURL.appendingPathComponent(".env")
      let contents = "MANGO_AI_PROVIDER=\(provider)\nMANGO_AI_API_KEY=\(apiKey)\nMANGO_AI_MODEL=\(model)\n"
      try contents.write(to: envURL, atomically: true, encoding: .utf8)
      try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: envURL.path)
      environment["MANGO_AI_PROVIDER"] = provider
      environment["MANGO_AI_API_KEY"] = apiKey
      environment["MANGO_AI_MODEL"] = model
      return jsonResponse(status: 200, payload: [
        "ok": true,
        "configured": true,
        "provider": provider,
        "model": model
      ])
    } catch {
      return jsonResponse(status: 500, payload: ["error": "保存 API Key 失败，请检查本机权限。"])
    }
  }

  private func handleChat(_ body: Data, completion: @escaping (Data) -> Void) {
    guard body.count > 0, body.count <= 64 * 1024 else {
      completion(jsonResponse(status: 413, payload: ["error": "消息内容过长。"]))
      return
    }
    guard let payload = try? JSONSerialization.jsonObject(with: body) as? [String: Any],
          let messages = payload["messages"] as? [[String: Any]],
          !messages.isEmpty
    else {
      completion(jsonResponse(status: 400, payload: ["error": "请求格式不正确。"]))
      return
    }

    var cleaned: [[String: String]] = []
    for item in messages.suffix(12) {
      guard let role = item["role"] as? String,
            ["user", "assistant"].contains(role),
            var content = item["content"] as? String
      else { continue }
      content = content.trimmingCharacters(in: .whitespacesAndNewlines)
      if !content.isEmpty {
        cleaned.append(["role": role, "content": String(content.prefix(4000))])
      }
    }
    guard let last = cleaned.last, last["role"] == "user" else {
      completion(jsonResponse(status: 400, payload: ["error": "最后一条消息必须是用户问题。"]))
      return
    }

    let provider = configuredProvider()
    let apiKey = configuredAPIKey()
    guard !apiKey.isEmpty else {
      completion(jsonResponse(status: 503, payload: ["error": "尚未设置 API Key，请设置后再聊天。"]))
      return
    }

    let requestedMode = payload["mode"] as? String
    let mode = ["fast", "thinking"].contains(requestedMode ?? "") ? requestedMode! : configuredMode()
    var upstreamMessages: [[String: String]] = [["role": "system", "content": mangoSystemPrompt]]
    upstreamMessages.append(contentsOf: cleaned)

    var upstreamPayload: [String: Any] = [
      "model": configuredModel(provider: provider),
      "messages": upstreamMessages,
      "stream": false,
      "temperature": 0.5,
      "max_tokens": 1200
    ]
    if provider == "deepseek", mode == "thinking" {
      upstreamPayload["thinking"] = ["type": "enabled"]
    }

    sendUpstreamChat(provider: provider, payload: upstreamPayload, completion: completion) { answer in
      ["message": answer]
    }
  }

  private func handleParseReminder(_ body: Data, completion: @escaping (Data) -> Void) {
    guard body.count > 0, body.count <= 8192 else {
      completion(jsonResponse(status: 413, payload: ["error": "提醒内容过长。"]))
      return
    }
    guard let payload = try? JSONSerialization.jsonObject(with: body) as? [String: Any],
          var text = payload["text"] as? String
    else {
      completion(jsonResponse(status: 400, payload: ["error": "请求格式不正确。"]))
      return
    }
    text = text.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !text.isEmpty else {
      completion(jsonResponse(status: 400, payload: ["error": "请输入提醒内容。"]))
      return
    }

    let provider = configuredProvider()
    let apiKey = configuredAPIKey()
    guard !apiKey.isEmpty else {
      completion(jsonResponse(status: 503, payload: ["error": "尚未设置 API Key，请设置后再使用智能解析。"]))
      return
    }

    let now = (payload["now"] as? String) ?? ISO8601DateFormatter().string(from: Date())
    let systemPrompt = """
      你是提醒时间解析器。只返回一个 JSON 对象，不要 Markdown，不要解释。
      当前时间是 \(now)。请按中国用户习惯理解中文提醒。
      如果可以确定提醒时间，返回：
      {"event":"事项名称","trigger_at":"YYYY-MM-DDTHH:mm:ss+08:00","needs_clarification":false,"clarification":""}
      如果缺少必要信息或不确定，返回：
      {"event":"尽量提取的事项","trigger_at":null,"needs_clarification":true,"clarification":"一句简短中文追问或格式提示"}
      event 应去掉时间词和“提醒我”等提示词；trigger_at 必须是未来时间；不要编造过于不确定的具体时间。
      如果用户只给了日期、星期、月份日期，或只说“早上/下午/晚上”等大致时间但没有具体钟点，不要默认 00:00 或自行猜测，必须 needs_clarification=true，并询问“你想几点提醒？”。
      """
    let userPrompt = "提醒文本：\(String(text.prefix(500)))"
    let upstreamPayload: [String: Any] = [
      "model": configuredModel(provider: provider),
      "messages": [
        ["role": "system", "content": systemPrompt],
        ["role": "user", "content": userPrompt]
      ],
      "stream": false,
      "temperature": 0.1,
      "max_tokens": 300
    ]

    sendUpstreamChat(provider: provider, payload: upstreamPayload, completion: completion) { answer in
      let parsed = self.parseReminderJSON(answer)
      if parsed.isEmpty {
        return [
          "needs_clarification": true,
          "clarification": "没能识别出提醒时间，请换一种说法重新输入。"
        ]
      }
      return parsed
    }
  }

  private func sendUpstreamChat(
    provider: String,
    payload upstreamPayload: [String: Any],
    completion: @escaping (Data) -> Void,
    mapAnswer: @escaping (String) -> [String: Any]
  ) {
    let apiKey = configuredAPIKey()
    guard let requestBody = try? JSONSerialization.data(withJSONObject: upstreamPayload),
          let url = URL(string: configuredAPIURL(provider: provider))
    else {
      completion(jsonResponse(status: 502, payload: ["error": "模型服务请求失败，请稍后再试。"]))
      return
    }

    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.timeoutInterval = 45
    request.httpBody = requestBody
    request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
      guard let self else { return }
      if error != nil {
        completion(self.jsonResponse(status: 504, payload: ["error": "连接模型服务超时，请检查网络。"]))
        return
      }
      let statusCode = (response as? HTTPURLResponse)?.statusCode ?? 502
      guard (200..<300).contains(statusCode), let data else {
        completion(self.jsonResponse(status: 502, payload: ["error": self.upstreamErrorMessage(statusCode: statusCode, data: data)]))
        return
      }
      guard let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let choices = result["choices"] as? [[String: Any]],
            let message = choices.first?["message"] as? [String: Any]
      else {
        completion(self.jsonResponse(status: 502, payload: ["error": "模型服务返回格式异常，请稍后再试。"]))
        return
      }
      let rawAnswer = (message["content"] as? String) ?? (message["reasoning_content"] as? String) ?? ""
      let answer = rawAnswer.trimmingCharacters(in: .whitespacesAndNewlines).replacingOccurrences(of: "**", with: "")
      guard !answer.isEmpty else {
        completion(self.jsonResponse(status: 502, payload: ["error": "模型服务没有返回回答，请重新提问。"]))
        return
      }
      completion(self.jsonResponse(status: 200, payload: mapAnswer(answer)))
    }.resume()
  }

  private func parseReminderJSON(_ answer: String) -> [String: Any] {
    var text = answer.trimmingCharacters(in: .whitespacesAndNewlines)
    if text.hasPrefix("```") {
      text = text.replacingOccurrences(of: "```json", with: "")
        .replacingOccurrences(of: "```", with: "")
        .trimmingCharacters(in: .whitespacesAndNewlines)
    }
    if let start = text.firstIndex(of: "{"), let end = text.lastIndex(of: "}"), start <= end {
      text = String(text[start...end])
    }
    guard let data = text.data(using: .utf8),
          let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    else { return [:] }
    var result: [String: Any] = [
      "event": object["event"] as? String ?? "",
      "needs_clarification": object["needs_clarification"] as? Bool ?? false,
      "clarification": object["clarification"] as? String ?? ""
    ]
    if let triggerAt = object["trigger_at"] as? String, !triggerAt.isEmpty {
      result["trigger_at"] = triggerAt
    } else {
      result["trigger_at"] = NSNull()
    }
    return result
  }

  private func upstreamErrorMessage(statusCode: Int, data: Data?) -> String {
    var body = ""
    if let data,
       let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
       let error = result["error"] {
      if let errorObject = error as? [String: Any] {
        body = (errorObject["message"] as? String) ?? (errorObject["code"] as? String) ?? ""
      } else {
        body = "\(error)"
      }
    }
    let normalized = body.lowercased()
    if statusCode == 401 {
      return "API Key 无效，请检查后重新保存。"
    }
    if statusCode == 402 || statusCode == 403 ||
        normalized.contains("balance") ||
        normalized.contains("insufficient") ||
        normalized.contains("quota") ||
        normalized.contains("payment") {
      return "账户余额不足，请充值后重试。"
    }
    if statusCode == 429 {
      return "请求过于频繁或额度不足，请稍后再试。"
    }
    return "模型服务请求失败，请稍后再试。"
  }

  private func staticResponse(path: String, includeBody: Bool) -> Data {
    let rawPath = path == "/" ? "/mango-bird.html" : path
    let decoded = rawPath.removingPercentEncoding ?? rawPath
    let relative = decoded.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
    guard !relative.isEmpty,
          !relative.contains(".."),
          !relative.hasPrefix("/")
    else {
      return plainResponse(status: 403, body: "Forbidden")
    }
    let fileURL = resourceURL.appendingPathComponent(relative)
    guard fileURL.path.hasPrefix(resourceURL.path),
          FileManager.default.fileExists(atPath: fileURL.path),
          let body = try? Data(contentsOf: fileURL)
    else {
      return plainResponse(status: 404, body: "Not Found")
    }
    return response(
      status: 200,
      contentType: contentType(for: fileURL.pathExtension),
      body: includeBody ? body : Data()
    )
  }

  private func contentType(for fileExtension: String) -> String {
    switch fileExtension.lowercased() {
    case "html": return "text/html; charset=utf-8"
    case "js": return "text/javascript; charset=utf-8"
    case "css": return "text/css; charset=utf-8"
    case "json": return "application/json; charset=utf-8"
    case "png": return "image/png"
    case "jpg", "jpeg": return "image/jpeg"
    case "webp": return "image/webp"
    case "gif": return "image/gif"
    case "ico": return "image/x-icon"
    default: return "application/octet-stream"
    }
  }

  private func jsonResponse(status: Int, payload: [String: Any]) -> Data {
    let body = (try? JSONSerialization.data(withJSONObject: payload)) ?? Data("{}".utf8)
    return response(status: status, contentType: "application/json; charset=utf-8", body: body)
  }

  private func plainResponse(status: Int, body: String) -> Data {
    response(status: status, contentType: "text/plain; charset=utf-8", body: Data(body.utf8))
  }

  private func response(status: Int, contentType: String, body: Data) -> Data {
    let reason: String
    switch status {
    case 200: reason = "OK"
    case 400: reason = "Bad Request"
    case 403: reason = "Forbidden"
    case 404: reason = "Not Found"
    case 413: reason = "Payload Too Large"
    case 500: reason = "Internal Server Error"
    case 502: reason = "Bad Gateway"
    case 503: reason = "Service Unavailable"
    case 504: reason = "Gateway Timeout"
    default: reason = "OK"
    }
    var data = Data()
    data.append("HTTP/1.1 \(status) \(reason)\r\n".data(using: .utf8)!)
    data.append("Content-Type: \(contentType)\r\n".data(using: .utf8)!)
    data.append("Content-Length: \(body.count)\r\n".data(using: .utf8)!)
    data.append("Connection: close\r\n".data(using: .utf8)!)
    data.append("X-Content-Type-Options: nosniff\r\n".data(using: .utf8)!)
    data.append("Referrer-Policy: no-referrer\r\n".data(using: .utf8)!)
    data.append("\r\n".data(using: .utf8)!)
    data.append(body)
    return data
  }
}

final class MangoDesktopWindow: NSPanel {
  override var canBecomeKey: Bool { true }
  override var canBecomeMain: Bool { true }
}

final class MangoDesktopBridge: NSObject, WKScriptMessageHandler {
  weak var appDelegate: AppDelegate?

  func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
    guard message.name == "mangoDesktop" else { return }
    if let body = message.body as? [String: Any], body["action"] as? String == "activate" {
      appDelegate?.focusPetWindow()
    } else if let body = message.body as? [String: Any], body["action"] as? String == "quit" {
      NSApp.terminate(nil)
    }
  }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
  private var window: MangoDesktopWindow!
  private var webView: WKWebView!
  private var localServer: MangoLocalServer?
  private var pointerTimer: Timer?
  private var globalMouseMonitor: Any?
  private var lastIgnoresMouseEvents = false
  private let bridge = MangoDesktopBridge()

  func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.accessory)
    createApplicationMenu()
    bridge.appDelegate = self
    createWindow()
    startServer()
    startPointerPassThrough()
    startGlobalStageClickMonitor()
  }

  func applicationWillTerminate(_ notification: Notification) {
    pointerTimer?.invalidate()
    if let monitor = globalMouseMonitor {
      NSEvent.removeMonitor(monitor)
    }
    localServer?.stop()
    localServer = nil
  }

  private func createWindow() {
    let screenFrame = NSScreen.screens.reduce(NSScreen.main?.frame ?? .zero) { $0.union($1.frame) }
    let safeAreaScript = desktopSafeAreaScript(in: screenFrame)
    window = MangoDesktopWindow(
      contentRect: screenFrame,
      styleMask: [.borderless],
      backing: .buffered,
      defer: false
    )
    window.backgroundColor = .clear
    window.isOpaque = false
    window.hasShadow = false
    window.level = .floating
    window.collectionBehavior = [.canJoinAllSpaces, .stationary, .fullScreenAuxiliary]
    window.ignoresMouseEvents = true
    window.hidesOnDeactivate = false

    let userContentController = WKUserContentController()
    userContentController.add(bridge, name: "mangoDesktop")
    userContentController.addUserScript(WKUserScript(
      source: safeAreaScript,
      injectionTime: .atDocumentStart,
      forMainFrameOnly: true
    ))

    let configuration = WKWebViewConfiguration()
    configuration.userContentController = userContentController

    webView = WKWebView(frame: screenFrame, configuration: configuration)
    webView.autoresizingMask = [.width, .height]
    webView.setValue(false, forKey: "drawsBackground")
    webView.wantsLayer = true
    webView.layer?.backgroundColor = NSColor.clear.cgColor

    window.contentView = webView
    window.makeKeyAndOrderFront(nil)
  }

  private func createApplicationMenu() {
    let mainMenu = NSMenu()

    let appMenuItem = NSMenuItem()
    let appMenu = NSMenu()
    appMenu.addItem(
      withTitle: "Quit Mango Bird",
      action: #selector(NSApplication.terminate(_:)),
      keyEquivalent: "q"
    )
    appMenuItem.submenu = appMenu
    mainMenu.addItem(appMenuItem)

    let editMenuItem = NSMenuItem()
    let editMenu = NSMenu(title: "Edit")
    editMenu.addItem(
      withTitle: "Cut",
      action: #selector(NSText.cut(_:)),
      keyEquivalent: "x"
    )
    editMenu.addItem(
      withTitle: "Copy",
      action: #selector(NSText.copy(_:)),
      keyEquivalent: "c"
    )
    editMenu.addItem(
      withTitle: "Paste",
      action: #selector(NSText.paste(_:)),
      keyEquivalent: "v"
    )
    editMenu.addItem(
      withTitle: "Select All",
      action: #selector(NSText.selectAll(_:)),
      keyEquivalent: "a"
    )
    editMenuItem.submenu = editMenu
    mainMenu.addItem(editMenuItem)

    NSApp.mainMenu = mainMenu
  }

  private func desktopSafeAreaScript(in screenFrame: CGRect) -> String {
    let visibleFrame = NSScreen.main?.visibleFrame ?? screenFrame
    let left = max(0, visibleFrame.minX - screenFrame.minX)
    let top = max(0, screenFrame.maxY - visibleFrame.maxY)
    let right = min(screenFrame.width, visibleFrame.maxX - screenFrame.minX)
    let bottom = min(screenFrame.height, screenFrame.maxY - visibleFrame.minY)
    return """
      window.__mangoDesktopSafeArea = {
        left: \(Int(left.rounded())),
        top: \(Int(top.rounded())),
        right: \(Int(right.rounded())),
        bottom: \(Int(bottom.rounded()))
      };
      """
  }

  private func startServer() {
    guard let projectURL = Bundle.main.resourceURL?.appendingPathComponent("MangoBird"),
          FileManager.default.fileExists(atPath: projectURL.appendingPathComponent("mango-bird.html").path)
    else {
      showFatalError("找不到 MangoBird 资源目录。")
      return
    }

    guard let supportURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
      showFatalError("无法读取用户配置目录。")
      return
    }
    let configURL = supportURL.appendingPathComponent("Mango Bird")
    var environment = ProcessInfo.processInfo.environment
    environment.merge(loadLocalEnvironment(configURL: configURL)) { _, local in local }
    let server = MangoLocalServer(resourceURL: projectURL, configURL: configURL, environment: environment)
    localServer = server
    server.start { [weak self] result in
      switch result {
      case .success(let url):
        self?.load(url: url)
      case .failure(let error):
        self?.showFatalError("无法启动本地服务：\(error.localizedDescription)")
      }
    }
  }

  private func load(url: URL) {
    webView.load(URLRequest(url: url))
  }

  private func loadLocalEnvironment(configURL: URL) -> [String: String] {
    let envURL = configURL.appendingPathComponent(".env")
    guard let contents = try? String(contentsOf: envURL, encoding: .utf8) else {
      return [:]
    }

    var values: [String: String] = [:]
    for rawLine in contents.components(separatedBy: .newlines) {
      let line = rawLine.trimmingCharacters(in: .whitespacesAndNewlines)
      if line.isEmpty || line.hasPrefix("#") { continue }
      guard let equals = line.firstIndex(of: "=") else { continue }
      let key = String(line[..<equals]).trimmingCharacters(in: .whitespacesAndNewlines)
      var value = String(line[line.index(after: equals)...]).trimmingCharacters(in: .whitespacesAndNewlines)
      if value.hasPrefix("\""), value.hasSuffix("\""), value.count >= 2 {
        value.removeFirst()
        value.removeLast()
      }
      if !key.isEmpty {
        values[key] = value
      }
    }
    return values
  }

  private func startPointerPassThrough() {
    pointerTimer = Timer.scheduledTimer(withTimeInterval: 0.016, repeats: true) { [weak self] _ in
      self?.updatePointerPassThrough()
    }
  }

  private func startGlobalStageClickMonitor() {
    globalMouseMonitor = NSEvent.addGlobalMonitorForEvents(matching: [.leftMouseDown]) { [weak self] event in
      self?.forwardGlobalStageClick(event)
    }
  }

  private func forwardGlobalStageClick(_ event: NSEvent) {
    guard let window, let webView else { return }
    let isDoubleClick = event.clickCount >= 2
    let point = NSEvent.mouseLocation
    let frame = window.frame
    let x = point.x - frame.minX
    let y = frame.maxY - point.y
    guard x >= 0, y >= 0, x <= frame.width, y <= frame.height else { return }

    let clickX = Int(x)
    let clickY = Int(y)
    let script = """
      (async () => {
        const x = \(clickX);
        const y = \(clickY);
        const isDoubleClick = \(isDoubleClick ? "true" : "false");
        if (window.isMangoPointerInteractive && window.isMangoPointerInteractive(x, y)) {
          return window.desktopForwardClick ? window.desktopForwardClick(x, y, isDoubleClick) : false;
        }
        return false;
      })()
      """
    DispatchQueue.main.async {
      webView.evaluateJavaScript(script) { result, _ in
        if result as? Bool == true { return }
      }
    }
  }

  private func updatePointerPassThrough() {
    guard let window, let webView else { return }
    let mouse = NSEvent.mouseLocation
    let frame = window.frame
    let x = mouse.x - frame.minX
    let y = frame.maxY - mouse.y
    guard x >= 0, y >= 0, x <= frame.width, y <= frame.height else {
      setIgnoresMouseEvents(true)
      return
    }

    let script = "window.isMangoPointerInteractive ? window.isMangoPointerInteractive(\(Int(x)), \(Int(y))) : false"
    webView.evaluateJavaScript(script) { [weak self] result, _ in
      let interactive = result as? Bool ?? false
      self?.setIgnoresMouseEvents(!interactive)
    }
  }

  private func setIgnoresMouseEvents(_ ignores: Bool) {
    guard ignores != lastIgnoresMouseEvents else { return }
    lastIgnoresMouseEvents = ignores
    window?.ignoresMouseEvents = ignores
    if !ignores {
      focusPetWindow()
    }
  }

  func focusPetWindow() {
    window?.ignoresMouseEvents = false
    lastIgnoresMouseEvents = false
    NSApp.activate(ignoringOtherApps: true)
    window?.makeKeyAndOrderFront(nil)
  }

  private func showFatalError(_ message: String) {
    let alert = NSAlert()
    alert.messageText = "Mango Bird 启动失败"
    alert.informativeText = message
    alert.runModal()
    NSApp.terminate(nil)
  }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
