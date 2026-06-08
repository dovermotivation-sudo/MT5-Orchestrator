#!/usr/bin/env python3
import http.server
import json
import urllib.parse

class MockBhionexHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if path == "/api/bot/active-subscriptions":
            api_key = self.headers.get("x-bot-api-key")
            if not api_key:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "message": "Unauthorized: Missing x-bot-api-key header"
                }).encode("utf-8"))
                return
                
            include_creds = query_params.get("includeCredentials", ["false"])[0] == "true"
            
            users = [
                {
                    "userId": "user_mock_1",
                    "userEmail": "john.doe@example.com",
                    "userStatus": "active",
                    "brokerName": "IC Markets",
                    "equityAmount": 1000,
                    "mt5Account": {
                        "loginId": "25500730",
                        "server": "VantageMarkets-Demo",
                        "password": ""
                    },
                    "mt5AccountStatus": "connected",
                    "activeSubscriptionId": "sub_1",
                    "scriptCode": "SCRIPT_1",
                    "subscriptionStatus": "active",
                    "subscriptionStartDate": "2026-06-02T00:00:00.000Z",
                    "subscriptionExpiryDate": "2026-07-02T00:00:00.000Z",
                    "threshold": {
                        "startingEquity": 1000,
                        "targetEquity": 1060,
                        "currentEquity": 1000,
                        "remainingToTarget": 60,
                        "status": "eligible"
                    },
                    "eligibleForMoreTrades": True,
                    "status": "active"
                },
                {
                    "userId": "user_mock_2",
                    "userEmail": "jane.smith@example.com",
                    "userStatus": "active",
                    "brokerName": "Vantage Markets",
                    "equityAmount": 2000,
                    "mt5Account": {
                        "loginId": "25506235",
                        "server": "VantageMarkets-Demo",
                        "password": ""
                    },
                    "mt5AccountStatus": "connected",
                    "activeSubscriptionId": "sub_2",
                    "scriptCode": "SCRIPT_2",
                    "subscriptionStatus": "active",
                    "subscriptionStartDate": "2026-06-02T00:00:00.000Z",
                    "subscriptionExpiryDate": "2026-07-02T00:00:00.000Z",
                    "threshold": {
                        "startingEquity": 2000,
                        "targetEquity": 2120,
                        "currentEquity": 2000,
                        "remainingToTarget": 120,
                        "status": "eligible"
                    },
                    "eligibleForMoreTrades": True,
                    "status": "active"
                }
            ]
            
            if include_creds:
                users[0]["mt5Account"]["password"] = "lIbY^^n1"
                users[1]["mt5Account"]["password"] = "iH17ogZ%"
                
            response = {
                "success": True,
                "users": users,
                "pagination": {
                    "page": 1,
                    "limit": 100,
                    "total": 2,
                    "pages": 1
                }
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return
            
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": False,
            "message": f"Route '{path}' not found."
        }).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        api_key = self.headers.get("x-bot-api-key")
        if not api_key:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "message": "Unauthorized: Missing x-bot-api-key header"
            }).encode("utf-8"))
            return
            
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            payload = json.loads(post_data)
        except Exception:
            payload = {}
            
        if path == "/api/bot/trades":
            print(f"[Mock Server] Received trade sync: Ticket={payload.get('externalTradeId')}, Symbol={payload.get('symbol')}, P/L={payload.get('profitLoss')}")
            
            response = {
                "success": True,
                "trade": {
                    "_id": "mock_trade_id_xyz",
                    "user": payload.get("userId"),
                    "scriptCode": payload.get("scriptCode"),
                    "symbol": payload.get("symbol"),
                    "tradeType": payload.get("tradeType"),
                    "profitLoss": payload.get("profitLoss"),
                    "status": "closed"
                },
                "tradeCycle": {
                    "_id": "mock_cycle_id_123",
                    "startingEquity": 1000,
                    "targetEquity": 1060,
                    "currentEquity": 1030,
                    "netProfitLoss": 30,
                    "remainingToTarget": 30,
                    "status": "eligible"
                },
                "eligibleForMoreTrades": True
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return
            
        elif path == "/api/bot/trading-summary":
            print(f"[Mock Server] Received status summary sync: User={payload.get('userId')}, Balance={payload.get('currentBalance')}, Net P/L={payload.get('netProfitLoss')}")
            
            response = {
                "success": True,
                "tradingReport": {
                    "_id": "mock_report_id_abc",
                    "user": payload.get("userId"),
                    "scriptCode": payload.get("scriptCode"),
                    "currentBalance": payload.get("currentBalance"),
                    "netProfitLoss": payload.get("netProfitLoss"),
                    "mt5AccountStatus": payload.get("mt5AccountStatus"),
                    "lastSyncAt": payload.get("lastSyncAt")
                }
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return
            
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "success": False,
            "message": f"Route '{path}' not found."
        }).encode("utf-8"))

def main():
    port = 5000
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, MockBhionexHandler)
    print(f"Mock Bhionex API Server is running on http://localhost:{port}/")
    print(f"To use this server, update your `.env` file to set:")
    print(f"API_BASE_URL=http://localhost:{port}")
    print("\nPress Ctrl+C to stop the server.")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping mock server.")
        httpd.server_close()

if __name__ == "__main__":
    main()
