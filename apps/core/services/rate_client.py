import requests
import json
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)


class RateServiceClient:
    """Клиент для взаимодействия с FastAPI сервисом курсов"""
    
    RATES_SERVICE_URL = getattr(settings, 'RATES_SERVICE_URL', 'http://localhost:8001')
    TIMEOUT = getattr(settings, 'RATES_SERVICE_TIMEOUT', 5)
    CACHE_TIMEOUT = getattr(settings, 'RATES_CACHE_TIMEOUT', 300)  # 5 минут
    
    @classmethod
    def get_rate(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """
        Получить курс валюты из сервиса курсов
        Возвращает Decimal или None при ошибке
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()
        
        if from_currency == to_currency:
            return Decimal('1.000000')

        cache_key = f"rate_{from_currency}_{to_currency}"
        cached_rate = cache.get(cache_key)
        if cached_rate is not None:
            logger.info(f"Rate {from_currency}/{to_currency} from Django cache: {cached_rate}")
            return Decimal(str(cached_rate))
        
        try:
            url = f"{cls.RATES_SERVICE_URL}/rates/{from_currency}/{to_currency}"
            
            response = requests.get(
                url,
                timeout=cls.TIMEOUT,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                rate = Decimal(str(data['rate']))
                
                cache.set(cache_key, float(rate), cls.CACHE_TIMEOUT)
                
                logger.info(f"Rate {from_currency}/{to_currency} from service: {rate}")
                return rate
            else:
                logger.error(f"Rate service error: {response.status_code} - {response.text}")
                return cls._get_fallback_rate(from_currency, to_currency)
                
        except requests.exceptions.Timeout:
            logger.error(f"Rate service timeout for {from_currency}/{to_currency}")
            return cls._get_fallback_rate(from_currency, to_currency)
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Rate service connection error for {from_currency}/{to_currency}")
            return cls._get_fallback_rate(from_currency, to_currency)
            
        except Exception as e:
            logger.error(f"Rate service error: {str(e)}")
            return cls._get_fallback_rate(from_currency, to_currency)
    
    @classmethod
    def get_bulk_rates(cls, from_currency: str, to_currencies: list) -> Dict[str, Decimal]:
        """Получить курсы для одной валюты ко многим"""
        from_currency = from_currency.upper()
        to_currencies = [c.upper() for c in to_currencies]
        
        result = {}
        for to_currency in to_currencies:
            rate = cls.get_rate(from_currency, to_currency)
            if rate is not None:
                result[to_currency] = rate
        
        return result
    
    @classmethod
    def _get_fallback_rate(cls, from_currency: str, to_currency: str) -> Optional[Decimal]:
        """Получить резервный курс из локальной БД"""
        try:
            from ..models import ExchangeRate
            from django.utils import timezone
            
            rate_obj = ExchangeRate.objects.filter(
                from_currency=from_currency,
                to_currency=to_currency
            ).order_by('-timestamp').first()
            
            if rate_obj:
                logger.info(f"Using fallback rate: {rate_obj.rate}")
                return rate_obj.rate
            
            reverse_rate = ExchangeRate.objects.filter(
                from_currency=to_currency,
                to_currency=from_currency
            ).order_by('-timestamp').first()
            
            if reverse_rate:
                fallback_rate = Decimal('1.0') / reverse_rate.rate
                logger.info(f"Using reverse fallback rate: {fallback_rate}")
                return fallback_rate
                
            return None
            
        except Exception as e:
            logger.error(f"Fallback rate error: {str(e)}")
            return None
    
    @classmethod
    def health_check(cls) -> bool:
        """Проверка доступности сервиса"""
        try:
            url = f"{cls.RATES_SERVICE_URL}/rates/health"
            response = requests.get(url, timeout=2)
            return response.status_code == 200
        except:
            return False