from hybrid.aggregator import HybridAnonymizer

def test_addr_tail():
    t = "Республика Татарстан, Томск, пер. Чехова, д.7, кв. 14."
    spans = HybridAnonymizer(device="cpu").process(t)
    assert any(s.type=="ADDR" and "кв. 14" in s.text for s in spans)

def test_max_not_per():
    t = "Макс. скорость 60 км/ч. Коллега Макс Иванов пришёл."
    spans = HybridAnonymizer(device="cpu").process(t)
    assert any(s.type=="PER" and "Макс Иванов" in s.text for s in spans)
    assert not any(s.type=="PER" and s.text=="Макс." for s in spans)
