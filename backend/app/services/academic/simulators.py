import ipaddress
import re
from typing import List, Dict, Any, Optional
import sympy as sp
from sympy.logic.boolalg import to_cnf, to_dnf

# 1. OS CPU Scheduling Simulator
class CPUSchedulingSimulator:
    """Simulates FCFS, SJF, Round Robin, and Priority CPU scheduling algorithms."""

    @staticmethod
    def simulate_fcfs(processes: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Sort by arrival time
        sorted_procs = sorted(processes, key=lambda x: (x.get("arrival", 0), x.get("pid", "")))
        current_time = 0
        gantt = []
        metrics = []

        for p in sorted_procs:
            pid = p["pid"]
            at = p.get("arrival", 0)
            bt = p.get("burst", 1)

            if current_time < at:
                gantt.append({"pid": "IDLE", "start": current_time, "end": at})
                current_time = at

            start = current_time
            end = current_time + bt
            current_time = end

            ct = end
            tat = ct - at
            wt = tat - bt

            gantt.append({"pid": pid, "start": start, "end": end})
            metrics.append({
                "pid": pid,
                "arrival": at,
                "burst": bt,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            })

        avg_wt = sum(m["waiting_time"] for m in metrics) / max(1, len(metrics))
        avg_tat = sum(m["turnaround_time"] for m in metrics) / max(1, len(metrics))

        return {
            "algorithm": "First-Come, First-Served (FCFS)",
            "gantt_chart": gantt,
            "processes": metrics,
            "average_waiting_time": round(avg_wt, 2),
            "average_turnaround_time": round(avg_tat, 2),
        }

    @staticmethod
    def simulate_round_robin(processes: List[Dict[str, Any]], quantum: int = 2) -> Dict[str, Any]:
        quantum = max(1, quantum)
        procs = sorted(processes, key=lambda x: x.get("arrival", 0))
        rem_burst = {p["pid"]: p.get("burst", 1) for p in procs}
        proc_map = {p["pid"]: p for p in procs}
        
        current_time = 0
        queue = []
        visited = set()
        gantt = []
        completed = {}

        # Add initial arrived
        for p in procs:
            if p.get("arrival", 0) <= current_time and p["pid"] not in visited:
                queue.append(p["pid"])
                visited.add(p["pid"])

        while queue or any(rem_burst[p] > 0 for p in rem_burst):
            if not queue:
                # CPU idle until next arrival
                next_at = min(p.get("arrival", 0) for p in procs if rem_burst[p["pid"]] > 0)
                gantt.append({"pid": "IDLE", "start": current_time, "end": next_at})
                current_time = next_at
                for p in procs:
                    if p.get("arrival", 0) <= current_time and p["pid"] not in visited and rem_burst[p["pid"]] > 0:
                        queue.append(p["pid"])
                        visited.add(p["pid"])
                continue

            curr_pid = queue.pop(0)
            exec_time = min(quantum, rem_burst[curr_pid])
            start = current_time
            end = current_time + exec_time
            current_time = end
            rem_burst[curr_pid] -= exec_time

            gantt.append({"pid": curr_pid, "start": start, "end": end})

            # Check new arrivals during execution
            for p in procs:
                if p.get("arrival", 0) <= current_time and p["pid"] not in visited and rem_burst[p["pid"]] > 0:
                    queue.append(p["pid"])
                    visited.add(p["pid"])

            if rem_burst[curr_pid] > 0:
                queue.append(curr_pid)
            else:
                completed[curr_pid] = current_time

        # Compute metrics
        metrics = []
        for p in procs:
            pid = p["pid"]
            at = p.get("arrival", 0)
            bt = p.get("burst", 1)
            ct = completed.get(pid, 0)
            tat = ct - at
            wt = tat - bt
            metrics.append({
                "pid": pid,
                "arrival": at,
                "burst": bt,
                "completion_time": ct,
                "turnaround_time": tat,
                "waiting_time": wt,
            })

        avg_wt = sum(m["waiting_time"] for m in metrics) / max(1, len(metrics))
        avg_tat = sum(m["turnaround_time"] for m in metrics) / max(1, len(metrics))

        return {
            "algorithm": f"Round Robin (Quantum = {quantum})",
            "gantt_chart": gantt,
            "processes": metrics,
            "average_waiting_time": round(avg_wt, 2),
            "average_turnaround_time": round(avg_tat, 2),
        }


# 2. OS Banker's Deadlock Avoidance Simulator
class BankersAlgorithmSimulator:
    @staticmethod
    def simulate_safety(
        available: List[int],
        allocation: List[List[int]],
        max_matrix: List[List[int]],
        pids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        num_p = len(allocation)
        num_r = len(available)
        pids = pids or [f"P{i}" for i in range(num_p)]

        # Calculate Need Matrix = Max - Allocation
        need = []
        for i in range(num_p):
            need.append([max_matrix[i][j] - allocation[i][j] for j in range(num_r)])

        work = list(available)
        finish = [False] * num_p
        safe_sequence = []
        steps = []

        while len(safe_sequence) < num_p:
            allocated_in_round = False
            for i in range(num_p):
                if not finish[i]:
                    # Check if Need <= Work for all resources
                    if all(need[i][j] <= work[j] for j in range(num_r)):
                        prev_work = list(work)
                        # Process can complete and release resources
                        for j in range(num_r):
                            work[j] += allocation[i][j]
                        finish[i] = True
                        safe_sequence.append(pids[i])
                        allocated_in_round = True

                        steps.append({
                            "step": len(safe_sequence),
                            "allocated_process": pids[i],
                            "need": need[i],
                            "previous_work": prev_work,
                            "new_work": list(work),
                            "status": f"{pids[i]} can execute safely. Resources released.",
                        })
                        break

            if not allocated_in_round:
                # No process could proceed -> Unsafe state (Deadlock potential)
                break

        is_safe = (len(safe_sequence) == num_p)

        return {
            "is_safe": is_safe,
            "safe_sequence": safe_sequence if is_safe else [],
            "need_matrix": need,
            "final_available": work,
            "simulation_steps": steps,
            "conclusion": (
                f"System is in a SAFE state. Safe sequence: {' -> '.join(safe_sequence)}"
                if is_safe
                else "System is in an UNSAFE state. Deadlock could occur!"
            ),
        }


# 3. OS Page Replacement Simulator
class PageReplacementSimulator:
    @staticmethod
    def simulate_fifo(pages: List[int], num_frames: int) -> Dict[str, Any]:
        frames: List[int] = []
        timeline = []
        faults = 0
        hits = 0

        for idx, page in enumerate(pages):
            is_hit = page in frames
            if is_hit:
                hits += 1
            else:
                faults += 1
                if len(frames) < num_frames:
                    frames.append(page)
                else:
                    frames.pop(0)  # FIFO evicts oldest
                    frames.append(page)

            timeline.append({
                "page": page,
                "frames": list(frames),
                "is_hit": is_hit,
            })

        return {
            "algorithm": "FIFO Page Replacement",
            "frames_count": num_frames,
            "total_references": len(pages),
            "page_faults": faults,
            "page_hits": hits,
            "fault_ratio": round(faults / max(1, len(pages)), 3),
            "hit_ratio": round(hits / max(1, len(pages)), 3),
            "timeline": timeline,
        }

    @staticmethod
    def simulate_lru(pages: List[int], num_frames: int) -> Dict[str, Any]:
        frames: List[int] = []
        last_used: Dict[int, int] = {}
        timeline = []
        faults = 0
        hits = 0

        for idx, page in enumerate(pages):
            is_hit = page in frames
            last_used[page] = idx

            if is_hit:
                hits += 1
            else:
                faults += 1
                if len(frames) < num_frames:
                    frames.append(page)
                else:
                    # Evict page with smallest last_used index
                    lru_page = min(frames, key=lambda p: last_used[p])
                    frames.remove(lru_page)
                    frames.append(page)

            timeline.append({
                "page": page,
                "frames": list(frames),
                "is_hit": is_hit,
            })

        return {
            "algorithm": "LRU (Least Recently Used) Page Replacement",
            "frames_count": num_frames,
            "total_references": len(pages),
            "page_faults": faults,
            "page_hits": hits,
            "fault_ratio": round(faults / max(1, len(pages)), 3),
            "hit_ratio": round(hits / max(1, len(pages)), 3),
            "timeline": timeline,
        }


# 4. Computer Networks Subnetting Calculator
class SubnetCalculator:
    @staticmethod
    def calculate_subnet(ip_str: str, prefix_len: int) -> Dict[str, Any]:
        try:
            net = ipaddress.IPv4Network(f"{ip_str}/{prefix_len}", strict=False)
            total_hosts = net.num_addresses
            usable_hosts = max(0, total_hosts - 2) if prefix_len < 31 else total_hosts

            first_host = str(net.network_address + 1) if usable_hosts > 0 else str(net.network_address)
            last_host = str(net.broadcast_address - 1) if usable_hosts > 0 else str(net.broadcast_address)

            return {
                "success": True,
                "input_ip": ip_str,
                "cidr": prefix_len,
                "network_address": str(net.network_address),
                "broadcast_address": str(net.broadcast_address),
                "netmask": str(net.netmask),
                "hostmask": str(net.hostmask),
                "first_usable_ip": first_host,
                "last_usable_ip": last_host,
                "total_addresses": total_hosts,
                "usable_hosts": usable_hosts,
                "binary_netmask": "".join(f"{int(x):08b}." for x in str(net.netmask).split(".")).rstrip("."),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# 5. DLCD Truth Table Simulator
class LogicCircuitSimulator:
    @staticmethod
    def generate_truth_table(expression_str: str) -> Dict[str, Any]:
        try:
            # Parse boolean expression using SymPy
            clean_expr = re.sub(r"\band\b", "&", expression_str, flags=re.IGNORECASE)
            clean_expr = re.sub(r"\bor\b", "|", clean_expr, flags=re.IGNORECASE)
            clean_expr = re.sub(r"\bnot\b", "~", clean_expr, flags=re.IGNORECASE)
            clean_expr = re.sub(r"\bxor\b", "^", clean_expr, flags=re.IGNORECASE)
            expr = sp.sympify(clean_expr)
            free_symbols = sorted(list(expr.free_symbols), key=lambda s: s.name)
            var_names = [s.name for s in free_symbols]

            num_vars = len(var_names)
            total_combinations = 1 << num_vars

            rows = []
            minterms = []

            for i in range(total_combinations):
                val_dict = {}
                row_vals = {}
                for bit_idx, var in enumerate(var_names):
                    bit = (i >> (num_vars - 1 - bit_idx)) & 1
                    val_dict[free_symbols[bit_idx]] = bool(bit)
                    row_vals[var] = bit

                res = bool(expr.subs(val_dict))
                row_vals["Output"] = 1 if res else 0
                rows.append(row_vals)
                if res:
                    minterms.append(i)

            return {
                "success": True,
                "expression": expression_str,
                "variables": var_names,
                "total_rows": total_combinations,
                "minterms": minterms,
                "minterms_notation": f"\\Sigma m({', '.join(map(str, minterms))})",
                "table": rows,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


cpu_scheduler = CPUSchedulingSimulator()
bankers_simulator = BankersAlgorithmSimulator()
page_simulator = PageReplacementSimulator()
subnet_calculator = SubnetCalculator()
circuit_simulator = LogicCircuitSimulator()
