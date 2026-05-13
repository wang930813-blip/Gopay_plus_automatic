#!/bin/bash
# Stop services started by start.sh.
# Usage: ./end.sh

set -u

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Stop GoPay Plus services ==="

collect_pids_by_port() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
        return
    fi

    if command -v fuser >/dev/null 2>&1; then
        fuser "$port"/tcp 2>/dev/null | tr ' ' '\n' | sed '/^$/d' || true
    fi
}

collect_project_service_pids() {
    local proc
    local pid
    local cmd
    local cwd

    for proc in /proc/[0-9]*; do
        [ -d "$proc" ] || continue

        pid="${proc##*/}"
        [ "$pid" = "$$" ] && continue

        cmd="$(tr '\0' ' ' < "$proc/cmdline" 2>/dev/null || true)"
        [ -n "$cmd" ] || continue

        cwd="$(readlink "$proc/cwd" 2>/dev/null || true)"

        if [ "$cwd" = "$DIR/plus_gopay_links" ] && [[ "$cmd" == *"payment_server.py"* ]]; then
            echo "$pid"
            continue
        fi

        if [ "$cwd" = "$DIR" ] && [[ "$cmd" == *"orchestrator.py"* ]]; then
            echo "$pid"
            continue
        fi

        if [ "$cwd" = "$DIR/to_whatsapp" ] && [[ "$cmd" == *"node"* ]] && [[ "$cmd" == *"index.js"* ]]; then
            echo "$pid"
        fi
    done
}

unique_pids() {
    awk 'NF && $1 ~ /^[0-9]+$/ { seen[$1] = 1 } END { for (pid in seen) print pid }'
}

is_running() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

stop_pids() {
    local label="$1"
    shift
    local pids=("$@")
    local running=()
    local pid

    if [ "${#pids[@]}" -eq 0 ]; then
        echo "- $label: no process found"
        return
    fi

    echo "- $label: stopping PIDs ${pids[*]}"
    kill "${pids[@]}" 2>/dev/null || true

    for _ in 1 2 3 4 5; do
        running=()
        for pid in "${pids[@]}"; do
            if is_running "$pid"; then
                running+=("$pid")
            fi
        done

        if [ "${#running[@]}" -eq 0 ]; then
            echo "  stopped"
            return
        fi

        sleep 1
    done

    echo "  forcing PIDs ${running[*]}"
    kill -9 "${running[@]}" 2>/dev/null || true
}

readarray -t SERVICE_PIDS < <(
    collect_project_service_pids | unique_pids
)

stop_pids "project services" "${SERVICE_PIDS[@]}"

readarray -t PORT_PIDS < <(
    {
        collect_pids_by_port 50051
        collect_pids_by_port 8800
        collect_pids_by_port 50056
    } | unique_pids
)

stop_pids "ports 50051/8800/50056" "${PORT_PIDS[@]}"

echo ""
echo "Port status:"
for port in 50051 8800 50056; do
    if [ -n "$(collect_pids_by_port "$port")" ]; then
        echo "- :$port still in use"
    else
        echo "- :$port free"
    fi
done

echo "Done."
