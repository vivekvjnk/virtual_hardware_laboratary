// src/config/network.ts

/**
 * Centralized network and host configuration.
 *
 * Configurable via environment variables:
 * - VHL_BASE_URL: Full base URL prefix (e.g. "http://localhost", "http://127.0.0.1", "http://my-host")
 * - VHL_HOST / MOSAIC_HOST: Hostname (defaults to "localhost")
 * - VHL_PROTOCOL: Protocol ("http" or "https", defaults to "http")
 *
 * By default, points to localhost ("http://localhost").
 */

export const DEFAULT_HOST = "localhost";
export const DEFAULT_PROTOCOL = "http";
export const DEFAULT_BASE_URL = "http://localhost";

export function getHost(): string {
    return process.env.VHL_HOST || process.env.MOSAIC_HOST || DEFAULT_HOST;
}

export function getProtocol(): string {
    return process.env.VHL_PROTOCOL || DEFAULT_PROTOCOL;
}

export function getBaseUrl(): string {
    if (process.env.VHL_BASE_URL) {
        return process.env.VHL_BASE_URL.replace(/\/+$/, "");
    }
    return `${getProtocol()}://${getHost()}`;
}

export function formatUrl(port: number, pathname: string = ""): string {
    const base = getBaseUrl();
    const cleanPath = pathname ? (pathname.startsWith("/") ? pathname : `/${pathname}`) : "";
    return `${base}:${port}${cleanPath}`;
}

export function getClusterUrl(port: number): string {
    return formatUrl(port);
}
