import Cocoa
import CoreGraphics
import WebKit

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
  private var serverProcess: Process?
  private var stdoutPipe: Pipe?
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
    if let process = serverProcess, process.isRunning {
      process.terminate()
    }
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
          FileManager.default.fileExists(atPath: projectURL.appendingPathComponent("mango-bird-server.py").path)
    else {
      showFatalError("找不到 MangoBird 资源目录。")
      return
    }

    guard FileManager.default.fileExists(atPath: "/usr/bin/python3") else {
      showFatalError("找不到 /usr/bin/python3。请安装 macOS Command Line Tools 后重新打开 Mango Bird。")
      return
    }

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/usr/bin/python3")
    process.arguments = ["mango-bird-server.py"]
    process.currentDirectoryURL = projectURL

    var environment = ProcessInfo.processInfo.environment
    environment.merge(loadLocalEnvironment()) { _, local in local }
    environment["MANGO_BIRD_PORT"] = "0"
    environment["PYTHONUNBUFFERED"] = "1"
    process.environment = environment

    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = pipe
    stdoutPipe = pipe
    pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
      let text = String(data: handle.availableData, encoding: .utf8) ?? ""
      guard let url = self?.firstServerURL(in: text) else { return }
      DispatchQueue.main.async {
        self?.load(url: url)
      }
    }

    do {
      try process.run()
      serverProcess = process
    } catch {
      showFatalError("无法启动本地服务：\(error.localizedDescription)")
    }
  }

  private func firstServerURL(in text: String) -> URL? {
    guard let range = text.range(of: #"http://127\.0\.0\.1:\d+/mango-bird\.html"#, options: .regularExpression) else {
      return nil
    }
    var components = URLComponents(string: String(text[range]))
    components?.queryItems = [URLQueryItem(name: "desktop", value: "1")]
    return components?.url
  }

  private func load(url: URL) {
    webView.load(URLRequest(url: url))
  }

  private func loadLocalEnvironment() -> [String: String] {
    guard let supportURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first else {
      return [:]
    }
    let envURL = supportURL.appendingPathComponent("Mango Bird/.env")
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
