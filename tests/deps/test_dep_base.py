"""
Testes unitários para a classe DepBase
"""
import pytest
from unittest.mock import Mock, patch
from deps.dep_base import DepBase


class TestDepBase:
    """Testes para a classe base DepBase"""

    def test_dep_base_initialization(self, mock_worker):
        """Testa a inicialização da classe DepBase"""
        # Act
        dep = DepBase(engine=mock_worker)
        
        # Assert
        assert dep.name == "dep"
        assert dep.engine == mock_worker
        assert hasattr(dep, 'load')

    def test_dep_base_default_engine(self):
        """Testa inicialização com engine padrão"""
        # Act
        dep = DepBase()
        
        # Assert
        from engines.worker import Worker
        assert dep.engine == Worker

    def test_dep_base_load_method(self, mock_worker):
        """Testa que o método load é chamado na inicialização"""
        with patch.object(DepBase, 'load') as mock_load:
            # Act
            DepBase(engine=mock_worker)
            
            # Assert
            mock_load.assert_called_once()

    def test_dep_base_load_implementation(self):
        """Testa que o método load padrão não faz nada"""
        # Act
        dep = DepBase()
        
        # Assert
        # O método load padrão deve existir e não fazer nada
        assert callable(dep.load)
        # Não deve gerar exceção
        dep.load()

    def test_dep_base_name_attribute(self):
        """Testa que o atributo name está definido"""
        # Act
        dep = DepBase()
        
        # Assert
        assert hasattr(dep, 'name')
        assert dep.name == "dep"

    def test_dep_base_engine_attribute(self, mock_worker):
        """Testa que o atributo engine é definido corretamente"""
        # Act
        dep = DepBase(engine=mock_worker)
        
        # Assert
        assert hasattr(dep, 'engine')
        assert dep.engine == mock_worker

    def test_dep_base_inheritance(self):
        """Testa que DepBase pode ser herdada corretamente"""
        class TestDep(DepBase):
            name = "test_dep"
            
            def load(self):
                self.test_loaded = True
        
        # Act
        test_dep = TestDep()
        
        # Assert
        assert test_dep.name == "test_dep"
        assert hasattr(test_dep, 'test_loaded')
        assert test_dep.test_loaded is True

    def test_dep_base_custom_engine(self):
        """Testa inicialização com engine customizada"""
        custom_engine = Mock()
        
        # Act
        dep = DepBase(engine=custom_engine)
        
        # Assert
        assert dep.engine == custom_engine

    @pytest.mark.unit
    def test_dep_base_unit_marker(self):
        """Testa que o marcador unit funciona"""
        dep = DepBase()
        assert dep.name == "dep"
