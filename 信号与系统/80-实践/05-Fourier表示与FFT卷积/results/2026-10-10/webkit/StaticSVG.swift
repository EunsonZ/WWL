import AppKit
import Foundation
import WebKit

struct Item: Decodable { let source: String; let width: Double; let height: Double; let output: String }

final class Renderer: NSObject, WKNavigationDelegate {
    let items: [Item]
    let outputDirectory: URL
    var index = 0
    var view: WKWebView?
    var window: NSWindow?
    var results: [[String: Any]] = []
    init(items: [Item], outputDirectory: URL) {
        self.items = items; self.outputDirectory = outputDirectory
        super.init()
    }
    func fail(_ message: String) -> Never {
        FileHandle.standardError.write(Data((message + "\n").utf8))
        exit(1)
    }
    func next() {
        if index == items.count {
            let receipt: [String: Any] = ["renderer": "WKWebView.takeSnapshot with full SVG viewport", "websiteDataStore": "nonPersistent", "contentJavaScript": false, "networkNavigation": "denied", "images": results]
            do {
                let data = try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
                try data.write(to: outputDirectory.appendingPathComponent("webkit-render.json"), options: .withoutOverwriting)
                FileHandle.standardOutput.write(data); FileHandle.standardOutput.write(Data("\n".utf8))
            } catch { fail("receipt write: \(error)") }
            exit(0)
        }
        let item = items[index]
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.defaultWebpagePreferences.allowsContentJavaScript = false
        let frame = NSRect(x: 0, y: 0, width: item.width, height: item.height)
        let webview = WKWebView(frame: frame, configuration: configuration)
        webview.navigationDelegate = self
        // Dedicated offscreen document window; no screen capture or existing window access.
        let documentWindow = NSWindow(contentRect: frame, styleMask: [.borderless], backing: .buffered, defer: false)
        documentWindow.isReleasedWhenClosed = false
        documentWindow.setFrameOrigin(NSPoint(x: -10000, y: -10000))
        documentWindow.contentView = webview
        documentWindow.orderFrontRegardless()
        window = documentWindow; view = webview
        let source = URL(fileURLWithPath: item.source)
        print("LOAD \(source.path) viewport \(item.width)x\(item.height)")
        webview.loadFileURL(source, allowingReadAccessTo: source)
    }
    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        let requested = navigationAction.request.url
        let expected = URL(fileURLWithPath: items[index].source)
        decisionHandler(requested?.isFileURL == true && requested?.standardizedFileURL == expected.standardizedFileURL ? .allow : .cancel)
    }
    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.2) {
            let item = self.items[self.index]
            let snapshot = WKSnapshotConfiguration()
            snapshot.rect = NSRect(x: 0, y: 0, width: item.width, height: item.height)
            snapshot.snapshotWidth = NSNumber(value: item.width)
            snapshot.afterScreenUpdates = true
            webView.takeSnapshot(with: snapshot) { image, error in
                if let error = error { self.fail("snapshot: \(error)") }
                guard let image = image, let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil),
                      let data = NSBitmapImageRep(cgImage: cg).representation(using: .png, properties: [:]) else { self.fail("missing snapshot image") }
                let destination = self.outputDirectory.appendingPathComponent(item.output)
                do { try data.write(to: destination, options: .withoutOverwriting) }
                catch { self.fail("PNG write: \(error)") }
                self.results.append(["source": item.source, "output": destination.path, "viewportWidth": item.width, "viewportHeight": item.height, "pixelWidth": cg.width, "pixelHeight": cg.height])
                print("SNAPSHOT \(destination.path) \(cg.width)x\(cg.height)")
                self.window?.close(); self.window = nil; self.view = nil
                self.index += 1; self.next()
            }
        }
    }
    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) { fail("navigation: \(error)") }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) { fail("provisional navigation: \(error)") }
}

guard CommandLine.arguments.count == 3 else { fatalError("usage: StaticSVG manifest.json output-directory") }
let manifestURL = URL(fileURLWithPath: CommandLine.arguments[1])
let outputURL = URL(fileURLWithPath: CommandLine.arguments[2], isDirectory: true)
let data = try Data(contentsOf: manifestURL)
let items = try JSONDecoder().decode([Item].self, from: data)
let application = NSApplication.shared
application.setActivationPolicy(.prohibited)
let renderer = Renderer(items: items, outputDirectory: outputURL)
DispatchQueue.main.async { renderer.next() }
application.run()
