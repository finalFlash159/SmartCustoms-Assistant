import logging
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from tools.hscode import HSCodeTool, HSCodeDateTool, HSCodeDateRangeTool
from tools.hscode_supplier import HSCodeSupplierTool
from tools.hscode_supplier_date import HSCodeSupplierDateTool
from tools.hscode_supplier_daterange import HSCodeSupplierDateRangeTool
from tools.hscode_status import HSCodeStatusTool
from tools.hscode_supplier_status import HSCodeSupplierStatusTool
from tools.hscode_supplier_date_status import HSCodeSupplierDateStatusTool
from tools.hscode_supplier_daterange_status import HSCodeSupplierDateRangeStatusTool
from tools.productname import ProductNameSearchTool, ProductNameDateTool, ProductNameDateRangeTool, ProductNameStatusTool, ProductNameDateStatusTool, ProductNameDaterangeStatusTool
from langsmith import traceable

logger = logging.getLogger(__name__)

class ToolAgent:
    def __init__(self, package: str = "trial_package", model_name: str = "gpt-3.5-turbo", temperature: float = 0.0, db_config: dict = None):
        logger.info("Khởi tạo ToolAgent với model=%s, temperature=%.1f", model_name, temperature)
        
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        self.package = package
        self.hscode_tool = HSCodeTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_tool = HSCodeSupplierTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_date_tool = HSCodeSupplierDateTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_daterange_tool = HSCodeSupplierDateRangeTool(tool_agent=self, db_config=db_config)
        self.hscode_status_tool = HSCodeStatusTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_status_tool = HSCodeSupplierStatusTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_date_status_tool = HSCodeSupplierDateStatusTool(tool_agent=self, db_config=db_config)
        self.hscode_supplier_daterange_status_tool = HSCodeSupplierDateRangeStatusTool(tool_agent=self, db_config=db_config)
        self.productname_search_tool = ProductNameSearchTool(tool_agent=self, db_config=db_config)
        self.productname_date_tool = ProductNameDateTool(tool_agent=self, db_config=db_config)
        self.productname_daterange_tool = ProductNameDateRangeTool(tool_agent=self, db_config=db_config)
        self.productname_status_tool = ProductNameStatusTool(tool_agent=self, db_config=db_config)
        self.productname_date_status_tool = ProductNameDateStatusTool(tool_agent=self, db_config=db_config)
        self.productname_daterange_status_tool = ProductNameDaterangeStatusTool(tool_agent=self, db_config=db_config)
        self.hscode_date_tool = HSCodeDateTool(tool_agent=self, db_config=db_config)
        self.hscode_daterange_tool = HSCodeDateRangeTool(tool_agent=self, db_config=db_config)
        
        self.tools = {
            "HSCodeTool": self.hscode_tool,
            "HSCodeSupplierTool": self.hscode_supplier_tool,
            "HSCodeSupplierDateTool": self.hscode_supplier_date_tool,
            "HSCodeSupplierDateRangeTool": self.hscode_supplier_daterange_tool,
            "HSCodeStatusTool": self.hscode_status_tool,
            "HSCodeSupplierStatusTool": self.hscode_supplier_status_tool,
            "HSCodeSupplierDateStatusTool": self.hscode_supplier_date_status_tool,
            "HSCodeSupplierDateRangeStatusTool": self.hscode_supplier_daterange_status_tool,
            "ProductNameSearchTool": self.productname_search_tool,
            "ProductNameDateTool": self.productname_date_tool,
            "ProductNameDateRangeTool": self.productname_daterange_tool,
            "ProductNameStatusTool": self.productname_status_tool,
            "ProductNameDateStatusTool": self.productname_date_status_tool,
            "ProductNameDaterangeStatusTool": self.productname_daterange_status_tool,
            "HSCodeDateTool": self.hscode_date_tool,
            "HSCodeDateRangeTool": self.hscode_daterange_tool
        }
        self.tool_called = {tool_name: False for tool_name in self.tools}  # Theo dõi tool được gọi

        self.agent = initialize_agent(
            tools=[self.hscode_tool, self.hscode_supplier_tool, self.hscode_supplier_date_tool, self.hscode_supplier_daterange_tool, 
                   self.hscode_status_tool, self.hscode_supplier_status_tool, self.hscode_supplier_date_status_tool,
                     self.hscode_supplier_daterange_status_tool, self.productname_search_tool, self.productname_date_tool,
                   self.productname_daterange_tool, self.productname_status_tool, self.productname_date_status_tool,
                   self.productname_daterange_status_tool, self.hscode_date_tool, self.hscode_daterange_tool],
            llm=self.llm,
            agent=AgentType.OPENAI_FUNCTIONS,
            verbose=True,
        )
        logger.info("Đã khởi tạo agent (OPENAI_FUNCTIONS)")

    def set_package(self, package: str):
        self.package = package

    def get_package(self) -> str:
        return self.package  

    @traceable(run_type="llm")
    async def decide_tool_usage(self, query: str) -> bool:
        """
        Sử dụng LLM để quyết định xem truy vấn có cần sử dụng tool hay không.
        Prompt yêu cầu trả lời chỉ là 'YES' hoặc 'NO'.
        """
        
        system_prompt = (
            "Bạn là trợ lý AI chuyên phân tích truy vấn của người dùng. "
            "Xác định xem truy vấn sau có cần sử dụng tool để lấy thông tin HS code hoặc thông tin về sản phẩm, tên mặt hàng hay không."
            "Sử dụng tool khi người dùng hỏi hoặc tra cứu thông tin liên quan đến hscode, nhà cung cấp, trạng thái (nhập/xuất), thông tin liên quan đến mặt hàng,tên mặt hàng."
            "Khi người dùng hỏi về thông tin hoặc kết quả phân tích phân loại hoặc tìm kết quả phân tích cho mã .../cho sản phẩn ..., thì không cần sử dụng tool. "
            "Trả lời chỉ là 'YES' nếu cần, hoặc 'NO' nếu không cần."
        )
        user_prompt = f"Câu hỏi: {query}"
        decision_prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_prompt),
            HumanMessagePromptTemplate.from_template(user_prompt)
        ])
        decision_chain = decision_prompt | self.llm
        decision_response = await decision_chain.ainvoke({"input": query})
        decision = decision_response.content.strip().upper()
        logger.info("Quyết định sử dụng tool cho query '%s': %s", query, decision)
        return decision == "YES"

    @traceable(run_type="llm")
    def decide_and_run(self, query: str) -> str:
        self.tool_called = {tool_name: False for tool_name in self.tools}  # Reset trạng thái
        logger.info("Agent nhận query: %s", query)
        try:
            result_msg = self.agent.invoke({"input": query})
            logger.info("Result message: %s", result_msg)
            
            # Xác định tool nào được gọi và xử lý kết quả
            for tool_name, tool in self.tools.items():
                if self.tool_called[tool_name]:
                    if tool.is_summary:
                        logger.info("Tool %s đã được gọi và trả về kết quả tóm tắt.", tool_name)
                        logger.info("Kết quả tóm tắt: %s", tool.last_result)
                        return tool.last_result
                    else:
                        output = result_msg["output"]
                        return output if output else "TOOL CALLED BUT NO CONTENT"
            return "Mình không tìm thấy thông tin liên quan. Hãy kiểm tra lại câu hỏi của bạn nhé!😓"
        except Exception as e:
            return f"Agent xảy ra lỗi: {e}"
