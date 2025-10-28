from utils.logic import clasifica_categoria

def test_categoria_analista():
    assert clasifica_categoria(-1, "Analistas") == "Al día"
    assert clasifica_categoria(5, "Analistas") == "Atraso normal"
    assert clasifica_categoria(20, "Analistas") == "Atraso medio"
    assert clasifica_categoria(50, "Analistas") == "Atraso alto"
