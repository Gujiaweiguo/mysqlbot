import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def verify_url(url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False, "无效的 URL 格式"

        if parsed.scheme not in ["http", "https"]:
            return False, "URL 必须以 http 或 https 开头"

        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        request = Request(url=url, method="HEAD")
        with urlopen(request, timeout=timeout, context=ssl_context) as response:
            status_code = response.status

        if status_code < 400:
            return True, "URL 可达"
        else:
            return False, f"服务器返回错误状态码: {status_code}"

    except TimeoutError:
        return False, f"连接超时 (>{timeout}秒)"
    except HTTPError as e:
        return False, f"服务器返回错误状态码: {e.code}"
    except URLError as e:
        return False, f"连接失败: {str(e)}"
    except Exception as e:
        return False, f"验证过程发生错误: {str(e)}"
