import pandas as pd
from rapidfuzz import fuzz, process
from typing import Dict, Optional, Tuple, List

# 读取 Excel 文件，并转换为列表形式的数据
suburbs_df = pd.read_excel("./data/db/db_suburbs.xlsx")
lga_df = pd.read_excel("./data/db/db_lga.xlsx")
policies_df = pd.read_excel("./data/db/db_policies.xlsx")

suburbs_data = suburbs_df.to_dict(orient="records")
lga_data = lga_df.to_dict(orient="records")
policies_data = policies_df.to_dict(orient="records")


class PolicyMatcher:
    def __init__(self, similarity_threshold=80):
        self.suburbs_data = suburbs_data
        self.lga_data = lga_data
        self.policies_data = policies_data
        self.similarity_threshold = similarity_threshold
        
        self._cache_reference_data()

    def _cache_reference_data(self):
        self.lga_names = list({item["lga"] for item in self.lga_data})
        self.suburb_list = list({item["suburb"] for item in self.suburbs_data})
        self.state_list = list({item["state"] for item in self.suburbs_data})

    def _log(self, message: str, log_info: List[str]):
        """将日志信息追加到 log_info 列表中"""
        log_info.append(message)

    # 以下方法用于在本地列表中查询数据，模拟 MongoDB 的 find_one/find 行为
    def _find_suburb_one(self, query: Dict) -> Optional[Dict]:
        for item in self.suburbs_data:
            if all(item.get(key) == value for key, value in query.items()):
                return item
        return None

    def _find_lga_one(self, query: Dict) -> Optional[Dict]:
        for item in self.lga_data:
            if all(item.get(key) == value for key, value in query.items()):
                return item
        return None

    def _find_suburbs_many(self, query: Dict) -> List[Dict]:
        return [item for item in self.suburbs_data if all(item.get(key) == value for key, value in query.items())]

    def _find_policies_many(self, query: Dict) -> List[Dict]:
        return [item for item in self.policies_data if all(item.get(key) == value for key, value in query.items())]

    def find_similar(
        self, query: str, choices: List[str], threshold: int = 80, log_info: List[str] = None
    ) -> Optional[Tuple[str, int]]:
        if not query or not choices:
            self._log(f"find_similar: Skipping as query='{query}' or choices are empty", log_info)
            return None

        matches = process.extract(query, choices, scorer=fuzz.ratio, limit=1)
        if matches:
            best_match = matches[0]
            if isinstance(best_match, tuple) and len(best_match) >= 2:
                match, similarity = best_match[:2]
                
                # 检查名称是否同时存在于 suburb 和 LGA 列表中
                is_suburb = match in self.suburb_list
                is_lga = match in self.lga_names
                
                if is_suburb and is_lga:
                    suburb_info = self._find_suburb_one({"suburb": match})
                    lga_info = self._find_lga_one({"lga": match})
                    self._log(
                        f"find_similar: Found match '{match}' exists as both suburb ({suburb_info['state'] if suburb_info else 'N/A'}) "
                        f"and LGA ({lga_info['state'] if lga_info else 'N/A'}) with similarity {similarity}% for query '{query}'",
                        log_info,
                    )
                elif is_suburb:
                    suburb_info = self._find_suburb_one({"suburb": match})
                    self._log(
                        f"find_similar: Found suburb: '{match}' ({suburb_info['state'] if suburb_info else 'N/A'}) "
                        f"with similarity {similarity}% for query '{query}'",
                        log_info,
                    )
                elif is_lga:
                    lga_info = self._find_lga_one({"lga": match})
                    self._log(
                        f"find_similar: Found LGA: '{match}' ({lga_info['state'] if lga_info else 'N/A'}) "
                        f"with similarity {similarity}% for query '{query}'",
                        log_info,
                    )
                
                if similarity >= threshold:
                    return match, similarity
                else:
                    self._log(f"Match below threshold {threshold}%: {match} (similarity: {similarity}%)", log_info)

        return None

    def search(
        self,
        query_suburb: Optional[str] = None,
        query_state: Optional[str] = None,
        query_lga: Optional[str] = None,
    ) -> Dict:
        log_info: List[str] = []

        # 如果仅提供 LGA，则走 LGA 搜索逻辑
        if query_lga and (not query_suburb or not query_state):
            return self._search_by_lga(query_lga, log_info, query_state)

        # 归一化输入
        query_suburb = query_suburb.strip().title() if query_suburb else None
        query_state = query_state.strip().upper() if query_state else None
        query_lga = query_lga.strip().title() if query_lga else None

        self._log(
            f"search: Searching with suburb='{query_suburb}', state='{query_state}', LGA='{query_lga}'", log_info
        )

        # 1. 完全匹配：suburb + state/LGA
        exact_match = self._exact_match(query_suburb, query_state, query_lga, log_info)
        if exact_match:
            self._log("search: Exact match found.", log_info)
            return self._build_response(exact_match, "Exact match", log_info)

        # 2. 模糊匹配 suburb，再精确匹配 state/LGA
        fuzzy_suburb = self.find_similar(query_suburb, self.suburb_list, self.similarity_threshold, log_info)
        if fuzzy_suburb:
            self._log(f"search: Fuzzy suburb match found: {fuzzy_suburb[0]}", log_info)
            match = self._exact_match(fuzzy_suburb[0], query_state, query_lga, log_info)
            if match:
                return self._build_response(match, f"Fuzzy suburb match (similarity: {fuzzy_suburb[1]}%)", log_info)

        # 3. 精确 suburb，模糊匹配 LGA
        fuzzy_lga = (
            self.find_similar(query_lga, self.lga_names, self.similarity_threshold, log_info)
            if query_lga
            else None
        )
        if fuzzy_lga:
            self._log(f"search: Fuzzy LGA match found: {fuzzy_lga[0]}", log_info)
            match = self._exact_match(query_suburb, query_state, fuzzy_lga[0], log_info)
            if match:
                return self._build_response(match, f"Fuzzy LGA match (similarity: {fuzzy_lga[1]}%)", log_info)

        # 4. 同时模糊匹配 suburb 和 LGA
        if fuzzy_suburb and fuzzy_lga:
            self._log(
                f"search: Trying fuzzy suburb '{fuzzy_suburb[0]}' with fuzzy LGA '{fuzzy_lga[0]}'", log_info
            )
            match = self._exact_match(fuzzy_suburb[0], query_state, fuzzy_lga[0], log_info)
            if match:
                return self._build_response(
                    match,
                    f"Fuzzy suburb + fuzzy LGA match (similarity: {fuzzy_suburb[1]}%, {fuzzy_lga[1]}%)",
                    log_info,
                )

        self._log("search: No match found.", log_info)
        print(f"ERROR: {log_info}")
        return {"log_info": log_info}

    def _search_by_lga(self, query_lga: str, log_info: List[str], query_state: Optional[str] = None) -> Dict:
        """仅根据 LGA 搜索，若提供 state 则也考虑 state"""
        self._log(f"_search_by_lga: Searching for LGA='{query_lga}', State='{query_state}'", log_info)
        
        query_lga = query_lga.strip().title()
        query_state = query_state.strip().upper() if query_state else None

        lga_query = {"lga": query_lga}
        if query_state:
            lga_query["state"] = query_state

        lga_match = self._find_lga_one(lga_query)
        if lga_match:
            match_type = "Exact LGA and State match" if query_state else "Exact LGA match"
            self._log(f"_search_by_lga: {match_type} found", log_info)
            return self._build_lga_response(lga_match, match_type, log_info)

        # 尝试模糊匹配 LGA
        fuzzy_lga = self.find_similar(query_lga, self.lga_names, self.similarity_threshold, log_info)
        if fuzzy_lga:
            lga_query = {"lga": fuzzy_lga[0]}
            if query_state:
                lga_query["state"] = query_state
            lga_match = self._find_lga_one(lga_query)
            if lga_match:
                match_type = f"Fuzzy LGA match (similarity: {fuzzy_lga[1]}%)"
                if query_state:
                    match_type += " and State considered"
                return self._build_lga_response(lga_match, match_type, log_info)

        self._log("_search_by_lga: No match found.", log_info)
        return {"log_info": log_info}

    def _exact_match(
        self, suburb: str, state: Optional[str], lga: Optional[str], log_info: List[str]
    ) -> Optional[Dict]:
        if not suburb:
            return None
        query = {"suburb": suburb}
        if state:
            query["state"] = state
        if lga:
            query["lga"] = lga

        self._log(f"_exact_match: Querying with {query}", log_info)
        match = self._find_suburb_one(query)
        if not match:
            self._log("_exact_match: No exact match found.", log_info)
        return match

    def _build_lga_response(self, lga_match: Dict, match_type: str, log_info: List[str]) -> Dict:
        """构建仅 LGA 搜索的响应"""
        lga = lga_match["lga"]
        suburbs = self._find_suburbs_many({"lga": lga})
        policies = self._find_policies_many({"lga": lga})
        
        result = {
            "lga_info": lga_match,
            "policies": policies,
            "match_type": match_type,
            "total_policies": len(policies),
            "log_info": log_info,
        }
        
        self._log(f"Match type: {match_type}", log_info)
        self._log(f"Found LGA: {lga} with {len(policies)} policies", log_info)
        self._log(f"Contains {len(suburbs)} suburbs", log_info)
        self._log_lga_result(result)
        return result

    def _build_response(self, match: Dict, match_type: str, log_info: List[str]) -> Dict:
        lga = match.get("lga")
        lga_info = self._find_lga_one({"lga": lga})
        lga_policies = self._find_policies_many({"lga": lga})

        result = {
            "suburb_info": match,
            "lga_info": lga_info,
            "policies": lga_policies,
            "match_type": match_type,
            "log_info": log_info,
        }
        self._log_result(result)
        return result

    def _log_lga_result(self, result: Dict):
        """输出 LGA 匹配结果的详细信息"""
        print(f"Match type: {result['match_type']}")
        print(f"Found: {result['lga_info']['lga']}, {result['lga_info']['state']}")

    def _log_result(self, result: Dict):
        """输出 suburb 匹配结果的详细信息"""
        print(f"Match type: {result['match_type']}")
        print(
            f"Found: {result['suburb_info']['suburb']}, {result['suburb_info']['postcode']}, "
            f"LGA: {result['suburb_info']['lga']}, {result['suburb_info']['state']}"
        )


if __name__ == "__main__":
    matcher = PolicyMatcher()
    print("hello")
    test_cases = [
        {"query_suburb": "Duck Cree", "query_lga": "Kyogles"},    # Fuzzy LGA
        {"query_suburb": "up ducks Creek", "query_state": "NSW"},   # Exact state
        {"query_suburb": "duckcreek", "query_lga": "Kyogle"},       # Normalized suburb
        {"query_suburb": "Crk", "query_state": "nsw"},              # Fuzzy suburb
        {"query_suburb": "Colo", "query_lga": "Hawkesbury"},
        {"query_suburb": "olmil", "query_lga": None}                # Exact match
    ]
    results = []
    for test in test_cases:
        print("\n" + "=" * 50)
        print(f"Query: {test}")
        results.append(matcher.search(**test))
