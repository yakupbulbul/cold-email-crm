import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.K6_BASE_URL || "http://127.0.0.1:8060";
const EMAIL = __ENV.K6_ADMIN_EMAIL || "admin@example.com";
const PASSWORD = __ENV.K6_ADMIN_PASSWORD || "";

export const options = {
  stages: [
    { duration: "1m", target: 3 },
    { duration: "3m", target: 3 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.02"],
    http_req_duration: ["p(95)<1800"],
  },
};

function authHeaders() {
  const login = http.post(
    `${BASE_URL}/api/v1/auth/login`,
    JSON.stringify({ email: EMAIL, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(login, { "soak login ok": (res) => res.status === 200 });
  return { Authorization: `Bearer ${login.json("access_token")}` };
}

export default function () {
  const headers = authHeaders();
  const params = { headers };
  const checks = [
    http.get(`${BASE_URL}/api/v1/auth/me`, params),
    http.get(`${BASE_URL}/api/v1/domains`, params),
    http.get(`${BASE_URL}/api/v1/ops/health/mailcow`, params),
  ];

  checks.forEach((response) => {
    check(response, { "soak request ok": (res) => res.status === 200 });
  });

  sleep(1);
}
