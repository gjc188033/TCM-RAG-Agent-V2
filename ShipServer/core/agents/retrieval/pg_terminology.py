"""
PostgreSQL 术语库连接类 — Ship-Agent

管理航运船代业务的术语主数据，提供：
  - 同义词查询（synonym）— 将用户输入的非规范术语映射到规范名称
  - 编码映射（code_mapping）— HS编码、港口UN LOCODE、集装箱编号校验
  - 规则校验（rule_check）— 基于术语关联的业务规则验证
  
表结构设计（建议）：

  terms（术语主表）：
    term_id       SERIAL PRIMARY KEY
    canonical     VARCHAR(200)  -- 规范名称
    category      VARCHAR(50)   -- 分类（port/vessel_type/cargo/regulation/service/...)
    description   TEXT
    created_at    TIMESTAMP DEFAULT now()

  aliases（别名表）：
    alias_id      SERIAL PRIMARY KEY
    term_id       INT REFERENCES terms(term_id)
    alias         VARCHAR(200)  -- 别名/简称/缩写
    alias_type    VARCHAR(20)   -- synonym/abbreviation/code

  codes（编码映射表）：
    code_id       SERIAL PRIMARY KEY
    term_id       INT REFERENCES terms(term_id)
    code_system   VARCHAR(50)   -- HS/UNLOCODE/IMO/BIC/...
    code_value    VARCHAR(50)
    description   TEXT

  rules（业务规则表）：
    rule_id       SERIAL PRIMARY KEY
    term_id       INT REFERENCES terms(term_id)
    rule_type     VARCHAR(50)   -- restriction/requirement/prohibition/calculation
    rule_content  TEXT
    severity      VARCHAR(20)   -- info/warning/critical
    effective_from DATE
    effective_to   DATE
"""

import psycopg2
import psycopg2.extras
import logging
from typing import List, Dict, Any, Optional
from .db_settings import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD

logger = logging.getLogger(__name__)


class TerminologyDB:
    """PostgreSQL 术语库客户端"""

    def __init__(self, host=PG_HOST, port=PG_PORT, database=PG_DATABASE,
                 user=PG_USER, password=PG_PASSWORD):
        """初始化 PostgreSQL 连接"""
        self.conn_params = {
            "host": host, "port": port, "database": database,
            "user": user, "password": password,
        }
        self._conn = None
        print(f"🔌 连接术语库 PostgreSQL: {host}:{port}/{database}")
        try:
            self._conn = psycopg2.connect(**self.conn_params)
            self._conn.autocommit = True
            print("✅ PostgreSQL 术语库连接成功")
        except Exception as e:
            print(f"⚠️ PostgreSQL 术语库连接失败: {e}")
            print("  术语库功能将降级运行")
            self._conn = None

    @property
    def is_connected(self) -> bool:
        return self._conn is not None and not self._conn.closed

    def _ensure_connection(self):
        """确保连接可用，如果断开则重连"""
        if not self.is_connected:
            try:
                self._conn = psycopg2.connect(**self.conn_params)
                self._conn.autocommit = True
            except Exception as e:
                logger.error(f"PostgreSQL 重连失败: {e}")
                return False
        return True

    # ────────────────────────────────────────
    # 同义词查询
    # ────────────────────────────────────────

    def lookup_synonym(self, term: str) -> Optional[Dict[str, Any]]:
        """
        查找术语的规范名称和相关信息

        参数:
            term: 用户输入的术语（可能是别名、缩写等）

        返回:
            {"term_id", "canonical", "category", "aliases", "matched_by"} 或 None
        """
        if not self._ensure_connection():
            return None

        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                # 1. 先精确匹配规范名称
                cur.execute(
                    "SELECT term_id, canonical, category, description FROM terms WHERE canonical = %s",
                    (term,)
                )
                row = cur.fetchone()
                if row:
                    return {**dict(row), "matched_by": "canonical", "aliases": self._get_aliases(cur, row["term_id"])}

                # 2. 精确匹配别名
                cur.execute(
                    """SELECT t.term_id, t.canonical, t.category, t.description, a.alias_type
                       FROM aliases a JOIN terms t ON a.term_id = t.term_id
                       WHERE a.alias = %s""",
                    (term,)
                )
                row = cur.fetchone()
                if row:
                    return {**dict(row), "matched_by": f"alias({row['alias_type']})",
                            "aliases": self._get_aliases(cur, row["term_id"])}

                # 3. 模糊匹配（pg_trgm similarity）
                cur.execute(
                    """SELECT t.term_id, t.canonical, t.category, t.description,
                              similarity(a.alias, %s) AS sim
                       FROM aliases a JOIN terms t ON a.term_id = t.term_id
                       WHERE similarity(a.alias, %s) > 0.3
                       ORDER BY sim DESC LIMIT 1""",
                    (term, term)
                )
                row = cur.fetchone()
                if row:
                    return {**dict(row), "matched_by": f"fuzzy(sim={row['sim']:.2f})",
                            "aliases": self._get_aliases(cur, row["term_id"])}

                return None

        except Exception as e:
            logger.error(f"同义词查询失败: {e}")
            return None

    def _get_aliases(self, cur, term_id: int) -> List[str]:
        """获取术语的所有别名"""
        cur.execute("SELECT alias FROM aliases WHERE term_id = %s", (term_id,))
        return [row["alias"] for row in cur.fetchall()]

    # ────────────────────────────────────────
    # 编码映射
    # ────────────────────────────────────────

    def lookup_code(self, code_value: str, code_system: str = None) -> Optional[Dict[str, Any]]:
        """
        根据编码查找对应的术语

        参数:
            code_value: 编码值（如 "CNSHA" / "2612.10" / "MSCU1234567"）
            code_system: 可选的编码体系限定（如 "UNLOCODE" / "HS" / "BIC"）

        返回:
            {"term_id","canonical","code_system","code_value","description"} 或 None
        """
        if not self._ensure_connection():
            return None

        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if code_system:
                    cur.execute(
                        """SELECT c.code_id, c.code_system, c.code_value, c.description AS code_desc,
                                  t.term_id, t.canonical, t.category
                           FROM codes c JOIN terms t ON c.term_id = t.term_id
                           WHERE c.code_value = %s AND c.code_system = %s""",
                        (code_value, code_system)
                    )
                else:
                    cur.execute(
                        """SELECT c.code_id, c.code_system, c.code_value, c.description AS code_desc,
                                  t.term_id, t.canonical, t.category
                           FROM codes c JOIN terms t ON c.term_id = t.term_id
                           WHERE c.code_value = %s""",
                        (code_value,)
                    )
                row = cur.fetchone()
                return dict(row) if row else None

        except Exception as e:
            logger.error(f"编码映射查询失败: {e}")
            return None

    # ────────────────────────────────────────
    # 规则校验
    # ────────────────────────────────────────

    def check_rules(self, term_id: int = None, term: str = None,
                    rule_type: str = None) -> List[Dict[str, Any]]:
        """
        查询与术语关联的业务规则

        参数:
            term_id: 术语ID（优先）
            term: 术语名（将先解析为term_id）
            rule_type: 可选过滤（restriction/requirement/prohibition/calculation）

        返回:
            规则列表 [{"rule_id","rule_type","rule_content","severity",...}]
        """
        if not self._ensure_connection():
            return []

        # 如果传了 term 但没传 term_id，先解析
        if term_id is None and term:
            result = self.lookup_synonym(term)
            if result:
                term_id = result["term_id"]
            else:
                return []

        if term_id is None:
            return []

        try:
            with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                sql = "SELECT * FROM rules WHERE term_id = %s"
                params = [term_id]

                if rule_type:
                    sql += " AND rule_type = %s"
                    params.append(rule_type)

                sql += " AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)"
                sql += " ORDER BY severity DESC, rule_id"

                cur.execute(sql, params)
                return [dict(r) for r in cur.fetchall()]

        except Exception as e:
            logger.error(f"规则校验查询失败: {e}")
            return []

    # ────────────────────────────────────────
    # 综合查询
    # ────────────────────────────────────────

    def comprehensive_lookup(self, term: str) -> Dict[str, Any]:
        """
        综合查询：同义归一 + 编码映射 + 关联规则，一次性返回

        返回:
            {
                "found": bool,
                "term_info": {...},  # 术语基本信息
                "codes": [...],      # 关联编码
                "rules": [...],      # 关联规则
            }
        """
        result = {"found": False, "term_info": None, "codes": [], "rules": []}

        term_info = self.lookup_synonym(term)
        if not term_info:
            # 尝试按编码查找
            code_info = self.lookup_code(term)
            if code_info:
                term_info = self.lookup_synonym(code_info["canonical"])

        if not term_info:
            return result

        result["found"] = True
        result["term_info"] = term_info

        term_id = term_info["term_id"]

        # 获取关联编码
        if self.is_connected:
            try:
                with self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("SELECT * FROM codes WHERE term_id = %s", (term_id,))
                    result["codes"] = [dict(r) for r in cur.fetchall()]
            except Exception:
                pass

        # 获取关联规则
        result["rules"] = self.check_rules(term_id=term_id)

        return result

    # ────────────────────────────────────────
    # 建表脚本
    # ────────────────────────────────────────

    def create_tables(self):
        """
        创建术语库表结构（首次部署时调用）
        """
        if not self._ensure_connection():
            raise ConnectionError("无法连接到 PostgreSQL")

        ddl = """
        CREATE EXTENSION IF NOT EXISTS pg_trgm;

        CREATE TABLE IF NOT EXISTS terms (
            term_id       SERIAL PRIMARY KEY,
            canonical     VARCHAR(200) NOT NULL,
            category      VARCHAR(50),
            description   TEXT,
            created_at    TIMESTAMP DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS aliases (
            alias_id      SERIAL PRIMARY KEY,
            term_id       INT REFERENCES terms(term_id) ON DELETE CASCADE,
            alias         VARCHAR(200) NOT NULL,
            alias_type    VARCHAR(20) DEFAULT 'synonym'
        );

        CREATE TABLE IF NOT EXISTS codes (
            code_id       SERIAL PRIMARY KEY,
            term_id       INT REFERENCES terms(term_id) ON DELETE CASCADE,
            code_system   VARCHAR(50) NOT NULL,
            code_value    VARCHAR(50) NOT NULL,
            description   TEXT
        );

        CREATE TABLE IF NOT EXISTS rules (
            rule_id       SERIAL PRIMARY KEY,
            term_id       INT REFERENCES terms(term_id) ON DELETE CASCADE,
            rule_type     VARCHAR(50),
            rule_content  TEXT,
            severity      VARCHAR(20) DEFAULT 'info',
            effective_from DATE,
            effective_to   DATE
        );

        -- 索引
        CREATE INDEX IF NOT EXISTS idx_terms_canonical ON terms(canonical);
        CREATE INDEX IF NOT EXISTS idx_aliases_alias ON aliases(alias);
        CREATE INDEX IF NOT EXISTS idx_aliases_alias_trgm ON aliases USING gin(alias gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_codes_value ON codes(code_value);
        CREATE INDEX IF NOT EXISTS idx_codes_system_value ON codes(code_system, code_value);
        CREATE INDEX IF NOT EXISTS idx_rules_term_id ON rules(term_id);
        """

        try:
            with self._conn.cursor() as cur:
                cur.execute(ddl)
            print("✅ 术语库表结构创建完成")
        except Exception as e:
            print(f"❌ 创建表结构失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self._conn and not self._conn.closed:
            self._conn.close()
            print("🔌 PostgreSQL 术语库连接已关闭")
