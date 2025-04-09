class RunnableLambda:
    def __init__(self, fn):
        self.fn = fn

    def invoke(self, input):
        return self.fn(input)

    def __call__(self, input):
        return self.fn(input)

    def __or__(self, other):
        # Cho phép xâu chuỗi các runnable: self | other
        def composed(input):
            result = self.invoke(input)
            return other(result)
        return RunnableLambda(composed)
    
    def __ror__(self, other):
        # Khi left operand là một hàm (hoặc bất kỳ thứ gì không hỗ trợ |), gọi __ror__ của RunnableLambda
        def composed(input):
            # Gọi hàm left operand (other) rồi sau đó gọi self
            return self.invoke(other(input))
        return RunnableLambda(composed)
