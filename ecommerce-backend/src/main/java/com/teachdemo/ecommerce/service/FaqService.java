package com.teachdemo.ecommerce.service;

import com.teachdemo.ecommerce.dto.FaqResponse;
import com.teachdemo.ecommerce.entity.FaqEntry;
import com.teachdemo.ecommerce.repository.FaqEntryRepository;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

@Service
public class FaqService {

    private final FaqEntryRepository faqEntryRepository;

    public FaqService(FaqEntryRepository faqEntryRepository) {
        this.faqEntryRepository = faqEntryRepository;
    }

    public List<FaqResponse> listFaq(String keyword) {
        List<FaqEntry> entries;
        if (StringUtils.hasText(keyword)) {
            entries = faqEntryRepository.findByCategoryContainingIgnoreCaseOrQuestionContainingIgnoreCaseOrAnswerContainingIgnoreCase(
                keyword,
                keyword,
                keyword);
        } else {
            entries = faqEntryRepository.findAll();
        }
        return entries.stream()
            .map(entry -> new FaqResponse(entry.getCategory(), entry.getQuestion(), entry.getAnswer()))
            .collect(Collectors.toList());
    }
}
